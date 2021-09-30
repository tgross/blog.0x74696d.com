---
categories:
- development
- golang
- bpf
date: 2021-08-28T12:00:00Z
title: "Challenges of BPF Tracing Go"
slug: challenges-of-bpf-tracing-go
---

Folks are rightfully excited about the performance benefits to Go
1.17's changes to function calling convention, but I was a little
disappointed to discover it doesn't make BPF `uretprobe`s possible. As
it turns out, I hadn't fully considered how Go's relocatable stacks
complicate the situation.

One of the advantages of Go's fast compile times is that "printf
debugging" gets you pretty far. You know the problem is somewhere
around a particular variable, so you drop in a `fmt.Printf` or
`log.Debug` or
[`spew.Dump`](https://pkg.go.dev/github.com/davecgh/go-spew) to
inspect the value at the point of interest. But I often work on
stateful systems, and in that environment this approach can be
limited. Recompiling for a new log statement and restarting may mean
losing the state that caused the problem, and logging can introduce
timing artifacts that obscure the bug. In those circumstances I reach
for BPF tools and in particular
[`bpftrace`](https://github.com/iovisor/bpftrace/).

One of the more powerful features of BPF for application developers is
user-level dynamic function instrumentation, implemented by `uprobe`
and `uretprobe`. A `uprobe` inserts a BPF probe at the point where a
function is called, and the `uretprobe` inserts a probe where the
function returns.

As a quick example, here's a function written in C:

```c
int sum(int a, int b) {
    return a+b;
}
```

And here's a `bpftrace` program that prints the program's arguments
and return value.

```awk
#!/usr/bin/env bpftrace

uprobe:./sum:"sum"
{
    printf("args: %d + %d\n", arg0, arg1);
}

uretprobe:./sum:"sum"
{
    printf("result: %d\n", reg("ax"));
}
```

If we run the `bpftrace` script, it'll pause waiting for us to run the
C program in another terminal, and then print the outputs:

```
$ sudo ./sum.bt
Attaching 2 probes...
args: 2 + 3
result: 5
^C
```

This is incredibly powerful for stateful applications because you can
attach these probes to a running program without recompiling it and
generally without impacting performance. This idea was pioneered in
[DTrace](http://dtrace.org/blogs/about/) and BPF brings this kind of
observability to Linux.

But Go's calling convention prior to Go 1.17 complicates tracing. In
the [System V AMD64 calling
convention](https://en.wikipedia.org/wiki/X86_calling_conventions#System_V_AMD64_ABI),
arguments are mostly passed in registers and return values are
returned in registers. BPF tools assume that compilers follow that
convention, but Go did not. Instead, Go followed the Plan9 calling
convention and passed arguments on the stack. Return values were
returned by popping off the stack.

For `uprobe`s this means we can't use the `arg` field that reads the
arguments out of the CPU registers expected by the AMD64 calling
convention. Instead we need to get them off the stack. This is mildly
annoying because you need to get the stack pointer, bump it to the
argument address, and then read the memory at that address. In
`bpftrace` 0.9.3 these are exposed as
[`sargX`](https://github.com/iovisor/bpftrace/issues/740) convenience
aliases, so this isn't too terrible.

The situation for `uretprobe`s is much worse. Instead of using a
thread for every goroutine, Go multiplexes goroutines across multiple
threads ("M:N scheduling"). So instead of each thread having a default
2MB stack, each goroutine has a tiny 2KB stack that's managed by the
runtime instead of the operating system. When the program needs to
grow the stack for a goroutine and there's not enough room, the
runtime copies the entire goroutine's stack to another place in memory
where it has enough room to expand.

When you configure a
[`uretprobe`](https://github.com/torvalds/linux/blob/v5.8/kernel/events/uprobes.c#L1861-L1925),
the kernel also creates a `uprobe` with a return probe handler. When
that `uprobe` is hit, it hijacks the return address of the probed
function and replaces it with the address of a "trampoline" with the
breakpoint.

But if the address has been moved by the time we hit it, the return
locations are no longer valid, and so a `uretprobe` that fires reads
into memory used somewhere else. This crashes the program!

To work around this, you can trace the function call from the
function's entry point with a `uprobe`, and then offset from there to
each return point of the function. This is incredibly gross and
involves disassembling the binary.

You probably don't spend your day looking at assembly and I sure as
heck don't either! So let's take a quick detour into reading
disassembled functions in go. Suppose this is our program:

```go
package main

import (
	"fmt"
	"os"
)

func swap(x, y string) (string, string) {
	return y, x
}

func main() {
	args := os.Args
	if len(args) < 3 {
		panic("needs 2 args")
	}
	a, b := swap(args[1], args[2])
	fmt.Println(a, b)
}
```

Because this program is trivial, Go will inline the `swap` function,
so for purposes of illustration we're going to compile it with `go
build -gcflags '-l' -o swapper .` to disable inlining.

First we'll disassemble the function in GDB. You could also do this in
`objdump` but we're going to want to poke around a bit here.

```
$ gdb --args ./swapper hello go
...
Reading symbols from ./swapper...
Loading Go Runtime support.
(gdb) b main.swap
Breakpoint 1 at 0x497800: file /home/tim/swapper/main.go, line 9
.
(gdb) run
Starting program: /home/tim/swapper/swapper hello world
[New LWP 3413956]
[New LWP 3413957]
[New LWP 3413958]
[New LWP 3413959]
[New LWP 3413960]

Thread 1 "swapper" hit Breakpoint 1, main.swap (x=..., y=..., ~r2=..., ~r3=...)
    at /home/tim/swapper/main.go:9
9               return y, x
(gdb) disas
Dump of assembler code for function main.swap:
=> 0x0000000000497800 <+0>:     mov    rax,QWORD PTR [rsp+0x18]
   0x0000000000497805 <+5>:     mov    QWORD PTR [rsp+0x28],rax
   0x000000000049780a <+10>:    mov    rax,QWORD PTR [rsp+0x20]
   0x000000000049780f <+15>:    mov    QWORD PTR [rsp+0x30],rax
   0x0000000000497814 <+20>:    mov    rax,QWORD PTR [rsp+0x8]
   0x0000000000497819 <+25>:    mov    QWORD PTR [rsp+0x38],rax
   0x000000000049781e <+30>:    mov    rax,QWORD PTR [rsp+0x10]
   0x0000000000497823 <+35>:    mov    QWORD PTR [rsp+0x40],rax
   0x0000000000497828 <+40>:    ret
End of assembler dump.
```

From a high-level view, we have 4 pointers to move: each string has a
length and a sequence of bytes, and there are two strings. The
function rearranges the pointers on the stack, and when we return
these values will be popped off the stack.

The first instruction is to move whatever is offset 0x18 from the
stack pointer (`rsp`) to the scratch register `rax`. Let's e`x`amine
that `a`ddress and then see if it's a readable `s`tring:

```
(gdb) x/a $rsp+0x18
0xc00011af18:   0x7fffffffddcd
(gdb) x/s 0x7fffffffddcd
0x7fffffffddcd: "go"
```

Cool! So that first instruction means we're moving the 64-bit pointer
(`QWORD PTR`) that points to the string's contents into the scratch
register. The next instruction moves the same pointer out of the
scratch space to the top of the stack (`rsp+0x28`).

The next instruction moves whatever is at offset 0x20 into the scratch
space. This is an integer: the length of our string!

```
(gdb) x/a $rsp+0x20
0xc00011af20:   0x2
```

That gets moved out of scratch space and onto the top of the stack as
well (`rsp+0x30`). The next 4 instructions repeat the same thing with
our other two arguments:

```
(gdb) x/a $rsp+0x8
0xc00011af08:   0x7fffffffddc7
(gdb) x/s 0x7fffffffddc7
0x7fffffffddc7: "hello"

(gdb) x/a $rsp+0x10
0xc00011af10:   0x5
```

We can `si`ngle step through 8 times until we hit the `ret`urn:

```
...
(gdb) si
0x0000000000497828 in main.swap (x=..., y=..., ~r2=..., ~r3=...)
    at /home/tim/swapper/main.go:9
9               return y, x
(gdb) disas
Dump of assembler code for function main.swap:
   0x0000000000497800 <+0>:     mov    rax,QWORD PTR [rsp+0x18]
   0x0000000000497805 <+5>:     mov    QWORD PTR [rsp+0x28],rax
   0x000000000049780a <+10>:    mov    rax,QWORD PTR [rsp+0x20]
   0x000000000049780f <+15>:    mov    QWORD PTR [rsp+0x30],rax
   0x0000000000497814 <+20>:    mov    rax,QWORD PTR [rsp+0x8]
   0x0000000000497819 <+25>:    mov    QWORD PTR [rsp+0x38],rax
   0x000000000049781e <+30>:    mov    rax,QWORD PTR [rsp+0x10]
   0x0000000000497823 <+35>:    mov    QWORD PTR [rsp+0x40],rax
=> 0x0000000000497828 <+40>:    ret
End of assembler dump.
```

The function has done all it's work and we're at the point where it's
going to return to the caller. Now we can examine the memory addresses
at the top of the stack:

```
(gdb) x/a $rsp+0x40
0xc00011af40:   0x5
(gdb) x/a $rsp+0x38
0xc00011af38:   0x7fffffffddc7
(gdb) x/s  0x7fffffffddc7
0x7fffffffddc7: "hello"
```

At this point, we can see we've moved our outputs into pointers offset
from the stack pointer, that point to our strings. These are on the
stack so it's last-in-first-out, which is admittedly a little extra
confusing here because the function's purpose is to swap the
strings.

If you're anything like me, you'll want a picture here:

![diagram of the stack, showing the contents of the bottom of the stack being swapped as they are moved to the top of the stack](/images/20210828/stack.svg)

How do we apply what we've just learned to BPF?

First, we now know that although the Go function has 2 arguments,
there are actually 4 arguments on the stack. So we'll need to grab two
pairs of stack args. We can print them correctly using the `str`
function of `bpftrace`: `str(sarg0, sarg1)` for `x` and `str(sarg2,
sarg3)` for `y`.

Next, although a `uretprobe` won't work, we can simulate one by adding
a `uprobe` that points to the offset of the return instruction. If you
look at the assembly again we see that's at `+40` so the `uprobe`
filter looks like `uprobe:./bin/swapper:"main.swap"+40`. When we hit
the probe, we can't simply look in return registers, but we need to
examine the stack pointer offsets we found for each argument
above. The final `bpftrace` program looks like the following:

```awk
#!/usr/bin/env bpftrace

uprobe:./swapper:"main.swap"
{
    printf("swapping \"%s\" and \"%s\"\n",
        str(sarg0, sarg1), str(sarg2, sarg3));
}

uprobe:./swapper:"main.swap"+40
{
    printf("results: \"%s\" and \"%s\"\n",
        str(*(reg("sp")+0x28), *(reg("sp")+0x30)),
        str(*(reg("sp")+0x38), *(reg("sp")+0x40))
        )
}
```

We run this program in one terminal while running `./swapper hello
world` in another terminal:

```
$ sudo ./swapper.bt
Attaching 2 probes...
swapping "hello" and "go"
results: "go" and "hello"
^C
```

As you can see, that's kind of a lot of work to do just for one return
probe. And if our function has multiple return points, we have to do
this for every one of them!

For a complex function like Nomad's FSM
[`Apply`](https://github.com/hashicorp/nomad/blob/v1.1.4/nomad/fsm.go#L193-L322)
method, I've had to lean on hideous tricks like generating a
`bpftrace` program:

```bash
#!/usr/bin/env bash

cat <<EOF
#!/usr/bin/env bpftrace
/*
Get Nomad FSM.Apply latency
Note: using sarg with offsets isn't really concurrency safe and emits a warning
*/

EOF

base=$(objdump --disassemble="github.com/hashicorp/nomad/nomad.(*nomadFSM).Apply" \
               -Mintel -S ./bin/nomad \
               | awk '/hashicorp/{print $1}' \
               | head -1)

objdump --disassemble="github.com/hashicorp/nomad/nomad.(*nomadFSM).Apply" \
        -Mintel -S ./bin/nomad \
        | awk -F' |:' '/ret/{print $2}' \
        | xargs -I % \
        python3 -c "print('uprobe:./bin/nomad:\"github.com/hashicorp/nomad/nomad.(*nomadFSM).Apply\"+' + hex(0x% - 0x$base))
print('{')
print('  @usecs = hist((nsecs - @start[str(*sarg1)]) / 1000);')
print('  delete(@start[str(*sarg1)]);')
print('}')
print('')
"
```

Which results in the following 300 line monstrosity:

<details>

```awk
#!/usr/bin/env bpftrace
/*
Get Nomad FSM.Apply latency
Note: using sarg with offsets isn't really concurrency safe and emits a warning
*/

uprobe:./bin/nomad:"github.com/hashicorp/nomad/nomad.(*nomadFSM).Apply"+0x1d3
{
  @usecs = hist((nsecs - @start[str(*sarg1)]) / 1000);
  delete(@start[str(*sarg1)]);
}

uprobe:./bin/nomad:"github.com/hashicorp/nomad/nomad.(*nomadFSM).Apply"+0x257
{
  @usecs = hist((nsecs - @start[str(*sarg1)]) / 1000);
  delete(@start[str(*sarg1)]);
}

uprobe:./bin/nomad:"github.com/hashicorp/nomad/nomad.(*nomadFSM).Apply"+0x2f3
{
  @usecs = hist((nsecs - @start[str(*sarg1)]) / 1000);
  delete(@start[str(*sarg1)]);
}

uprobe:./bin/nomad:"github.com/hashicorp/nomad/nomad.(*nomadFSM).Apply"+0x377
{
  @usecs = hist((nsecs - @start[str(*sarg1)]) / 1000);
  delete(@start[str(*sarg1)]);
}

uprobe:./bin/nomad:"github.com/hashicorp/nomad/nomad.(*nomadFSM).Apply"+0x3fb
{
  @usecs = hist((nsecs - @start[str(*sarg1)]) / 1000);
  delete(@start[str(*sarg1)]);
}

uprobe:./bin/nomad:"github.com/hashicorp/nomad/nomad.(*nomadFSM).Apply"+0x49b
{
  @usecs = hist((nsecs - @start[str(*sarg1)]) / 1000);
  delete(@start[str(*sarg1)]);
}

uprobe:./bin/nomad:"github.com/hashicorp/nomad/nomad.(*nomadFSM).Apply"+0x51b
{
  @usecs = hist((nsecs - @start[str(*sarg1)]) / 1000);
  delete(@start[str(*sarg1)]);
}

uprobe:./bin/nomad:"github.com/hashicorp/nomad/nomad.(*nomadFSM).Apply"+0x5a0
{
  @usecs = hist((nsecs - @start[str(*sarg1)]) / 1000);
  delete(@start[str(*sarg1)]);
}

uprobe:./bin/nomad:"github.com/hashicorp/nomad/nomad.(*nomadFSM).Apply"+0x634
{
  @usecs = hist((nsecs - @start[str(*sarg1)]) / 1000);
  delete(@start[str(*sarg1)]);
}

uprobe:./bin/nomad:"github.com/hashicorp/nomad/nomad.(*nomadFSM).Apply"+0x6b4
{
  @usecs = hist((nsecs - @start[str(*sarg1)]) / 1000);
  delete(@start[str(*sarg1)]);
}

uprobe:./bin/nomad:"github.com/hashicorp/nomad/nomad.(*nomadFSM).Apply"+0x738
{
  @usecs = hist((nsecs - @start[str(*sarg1)]) / 1000);
  delete(@start[str(*sarg1)]);
}

uprobe:./bin/nomad:"github.com/hashicorp/nomad/nomad.(*nomadFSM).Apply"+0x7e7
{
  @usecs = hist((nsecs - @start[str(*sarg1)]) / 1000);
  delete(@start[str(*sarg1)]);
}

uprobe:./bin/nomad:"github.com/hashicorp/nomad/nomad.(*nomadFSM).Apply"+0x86e
{
  @usecs = hist((nsecs - @start[str(*sarg1)]) / 1000);
  delete(@start[str(*sarg1)]);
}

uprobe:./bin/nomad:"github.com/hashicorp/nomad/nomad.(*nomadFSM).Apply"+0x8ee
{
  @usecs = hist((nsecs - @start[str(*sarg1)]) / 1000);
  delete(@start[str(*sarg1)]);
}

uprobe:./bin/nomad:"github.com/hashicorp/nomad/nomad.(*nomadFSM).Apply"+0x982
{
  @usecs = hist((nsecs - @start[str(*sarg1)]) / 1000);
  delete(@start[str(*sarg1)]);
}

uprobe:./bin/nomad:"github.com/hashicorp/nomad/nomad.(*nomadFSM).Apply"+0xa06
{
  @usecs = hist((nsecs - @start[str(*sarg1)]) / 1000);
  delete(@start[str(*sarg1)]);
}

uprobe:./bin/nomad:"github.com/hashicorp/nomad/nomad.(*nomadFSM).Apply"+0xa8e
{
  @usecs = hist((nsecs - @start[str(*sarg1)]) / 1000);
  delete(@start[str(*sarg1)]);
}

uprobe:./bin/nomad:"github.com/hashicorp/nomad/nomad.(*nomadFSM).Apply"+0xb27
{
  @usecs = hist((nsecs - @start[str(*sarg1)]) / 1000);
  delete(@start[str(*sarg1)]);
}

uprobe:./bin/nomad:"github.com/hashicorp/nomad/nomad.(*nomadFSM).Apply"+0xbae
{
  @usecs = hist((nsecs - @start[str(*sarg1)]) / 1000);
  delete(@start[str(*sarg1)]);
}

uprobe:./bin/nomad:"github.com/hashicorp/nomad/nomad.(*nomadFSM).Apply"+0xc2e
{
  @usecs = hist((nsecs - @start[str(*sarg1)]) / 1000);
  delete(@start[str(*sarg1)]);
}

uprobe:./bin/nomad:"github.com/hashicorp/nomad/nomad.(*nomadFSM).Apply"+0xcc2
{
  @usecs = hist((nsecs - @start[str(*sarg1)]) / 1000);
  delete(@start[str(*sarg1)]);
}

uprobe:./bin/nomad:"github.com/hashicorp/nomad/nomad.(*nomadFSM).Apply"+0xd46
{
  @usecs = hist((nsecs - @start[str(*sarg1)]) / 1000);
  delete(@start[str(*sarg1)]);
}

uprobe:./bin/nomad:"github.com/hashicorp/nomad/nomad.(*nomadFSM).Apply"+0xdce
{
  @usecs = hist((nsecs - @start[str(*sarg1)]) / 1000);
  delete(@start[str(*sarg1)]);
}

uprobe:./bin/nomad:"github.com/hashicorp/nomad/nomad.(*nomadFSM).Apply"+0xe77
{
  @usecs = hist((nsecs - @start[str(*sarg1)]) / 1000);
  delete(@start[str(*sarg1)]);
}

uprobe:./bin/nomad:"github.com/hashicorp/nomad/nomad.(*nomadFSM).Apply"+0xefb
{
  @usecs = hist((nsecs - @start[str(*sarg1)]) / 1000);
  delete(@start[str(*sarg1)]);
}

uprobe:./bin/nomad:"github.com/hashicorp/nomad/nomad.(*nomadFSM).Apply"+0xf80
{
  @usecs = hist((nsecs - @start[str(*sarg1)]) / 1000);
  delete(@start[str(*sarg1)]);
}

uprobe:./bin/nomad:"github.com/hashicorp/nomad/nomad.(*nomadFSM).Apply"+0x1014
{
  @usecs = hist((nsecs - @start[str(*sarg1)]) / 1000);
  delete(@start[str(*sarg1)]);
}

uprobe:./bin/nomad:"github.com/hashicorp/nomad/nomad.(*nomadFSM).Apply"+0x1098
{
  @usecs = hist((nsecs - @start[str(*sarg1)]) / 1000);
  delete(@start[str(*sarg1)]);
}

uprobe:./bin/nomad:"github.com/hashicorp/nomad/nomad.(*nomadFSM).Apply"+0x111c
{
  @usecs = hist((nsecs - @start[str(*sarg1)]) / 1000);
  delete(@start[str(*sarg1)]);
}

uprobe:./bin/nomad:"github.com/hashicorp/nomad/nomad.(*nomadFSM).Apply"+0x11b7
{
  @usecs = hist((nsecs - @start[str(*sarg1)]) / 1000);
  delete(@start[str(*sarg1)]);
}

uprobe:./bin/nomad:"github.com/hashicorp/nomad/nomad.(*nomadFSM).Apply"+0x123b
{
  @usecs = hist((nsecs - @start[str(*sarg1)]) / 1000);
  delete(@start[str(*sarg1)]);
}

uprobe:./bin/nomad:"github.com/hashicorp/nomad/nomad.(*nomadFSM).Apply"+0x12c0
{
  @usecs = hist((nsecs - @start[str(*sarg1)]) / 1000);
  delete(@start[str(*sarg1)]);
}

uprobe:./bin/nomad:"github.com/hashicorp/nomad/nomad.(*nomadFSM).Apply"+0x1350
{
  @usecs = hist((nsecs - @start[str(*sarg1)]) / 1000);
  delete(@start[str(*sarg1)]);
}

uprobe:./bin/nomad:"github.com/hashicorp/nomad/nomad.(*nomadFSM).Apply"+0x13d0
{
  @usecs = hist((nsecs - @start[str(*sarg1)]) / 1000);
  delete(@start[str(*sarg1)]);
}

uprobe:./bin/nomad:"github.com/hashicorp/nomad/nomad.(*nomadFSM).Apply"+0x1450
{
  @usecs = hist((nsecs - @start[str(*sarg1)]) / 1000);
  delete(@start[str(*sarg1)]);
}

uprobe:./bin/nomad:"github.com/hashicorp/nomad/nomad.(*nomadFSM).Apply"+0x14f7
{
  @usecs = hist((nsecs - @start[str(*sarg1)]) / 1000);
  delete(@start[str(*sarg1)]);
}

uprobe:./bin/nomad:"github.com/hashicorp/nomad/nomad.(*nomadFSM).Apply"+0x1577
{
  @usecs = hist((nsecs - @start[str(*sarg1)]) / 1000);
  delete(@start[str(*sarg1)]);
}

uprobe:./bin/nomad:"github.com/hashicorp/nomad/nomad.(*nomadFSM).Apply"+0x15f7
{
  @usecs = hist((nsecs - @start[str(*sarg1)]) / 1000);
  delete(@start[str(*sarg1)]);
}

uprobe:./bin/nomad:"github.com/hashicorp/nomad/nomad.(*nomadFSM).Apply"+0x168f
{
  @usecs = hist((nsecs - @start[str(*sarg1)]) / 1000);
  delete(@start[str(*sarg1)]);
}

uprobe:./bin/nomad:"github.com/hashicorp/nomad/nomad.(*nomadFSM).Apply"+0x170f
{
  @usecs = hist((nsecs - @start[str(*sarg1)]) / 1000);
  delete(@start[str(*sarg1)]);
}

uprobe:./bin/nomad:"github.com/hashicorp/nomad/nomad.(*nomadFSM).Apply"+0x178f
{
  @usecs = hist((nsecs - @start[str(*sarg1)]) / 1000);
  delete(@start[str(*sarg1)]);
}

uprobe:./bin/nomad:"github.com/hashicorp/nomad/nomad.(*nomadFSM).Apply"+0x18ca
{
  @usecs = hist((nsecs - @start[str(*sarg1)]) / 1000);
  delete(@start[str(*sarg1)]);
}

uprobe:./bin/nomad:"github.com/hashicorp/nomad/nomad.(*nomadFSM).Apply"+0x1948
{
  @usecs = hist((nsecs - @start[str(*sarg1)]) / 1000);
  delete(@start[str(*sarg1)]);
}

uprobe:./bin/nomad:"github.com/hashicorp/nomad/nomad.(*nomadFSM).Apply"+0x19ce
{
  @usecs = hist((nsecs - @start[str(*sarg1)]) / 1000);
  delete(@start[str(*sarg1)]);
}

uprobe:./bin/nomad:"github.com/hashicorp/nomad/nomad.(*nomadFSM).Apply"+0x1a52
{
  @usecs = hist((nsecs - @start[str(*sarg1)]) / 1000);
  delete(@start[str(*sarg1)]);
}

uprobe:./bin/nomad:"github.com/hashicorp/nomad/nomad.(*nomadFSM).Apply"+0x1a6d
{
  @usecs = hist((nsecs - @start[str(*sarg1)]) / 1000);
  delete(@start[str(*sarg1)]);
}

uprobe:./bin/nomad:"github.com/hashicorp/nomad/nomad.(*nomadFSM).Apply"+0x1b07
{
  @usecs = hist((nsecs - @start[str(*sarg1)]) / 1000);
  delete(@start[str(*sarg1)]);
}

uprobe:./bin/nomad:"github.com/hashicorp/nomad/nomad.(*nomadFSM).Apply"+0x1b87
{
  @usecs = hist((nsecs - @start[str(*sarg1)]) / 1000);
  delete(@start[str(*sarg1)]);
}

uprobe:./bin/nomad:"github.com/hashicorp/nomad/nomad.(*nomadFSM).Apply"+0x1c0e
{
  @usecs = hist((nsecs - @start[str(*sarg1)]) / 1000);
  delete(@start[str(*sarg1)]);
}
```

</details>

The new calling convention in Go 1.17 changes this situation for the
better, but leaves us short of working `uretprobe`s. Our same `swapper`
program compiled with Go 1.17 disassembles into the following:

```
(gdb) disas
Dump of assembler code for function main.swap:
=> 0x000000000047e260 <+0>:     mov    QWORD PTR [rsp+0x8],rax
   0x000000000047e265 <+5>:     mov    QWORD PTR [rsp+0x18],rcx
   0x000000000047e26a <+10>:    mov    rdx,rax
   0x000000000047e26d <+13>:    mov    rax,rcx
   0x000000000047e270 <+16>:    mov    rsi,rbx
   0x000000000047e273 <+19>:    mov    rbx,rdi
   0x000000000047e276 <+22>:    mov    rcx,rdx
   0x000000000047e279 <+25>:    mov    rdi,rsi
   0x000000000047e27c <+28>:    ret
End of assembler dump.
```

Everything is now in the argument registers, and with less pointer
indirection:

```
(gdb) x/s $rax
0x7fffffffddca: "hello"
(gdb) i r $rbx
rbx            0x5                 5
(gdb) x/s $rcx
0x7fffffffddd0: "go"
(gdb) i r $rdi
rdi            0x2                 2
```

(I'm honestly not sure why the second argument's length shows up in
`rdi` rather than `rdx`, so if you know I'd love to hear why!)

The return values also get placed into the registers, which means we
_should_ now be able to use a `uretprobe` to get the values out of
them. Our `bpftrace` program becomes much simpler:

```awk
#!/usr/bin/env bpftrace

uprobe:./swapper:"main.swap"
{
    printf("swapping \"%s\" and \"%s\"\n",
      str(reg("ax")), str(reg("cx")));
}

uretprobe:./swapper:"main.swap"
{
    printf("results: \"%s\" and \"%s\"\n",
      str(reg("ax")), str(reg("cx")));
}
```

```
$ sudo ./swapper.bt
Attaching 2 probes...
swapping "hello" and "go"
results: "go" and "hello"
^C
```

So what's the problem? Isn't this great? Well so far all the programs
we've looked at haven't allocated enough on the stack for the runtime
to resize it. This is where the `uretprobe` falls down.

Take a look at the following program. The `temp` variable never
escapes onto the heap (we can verify this by passing `-gcflags -m` to
the compiler), so we allocate `sizeof(Example) * count` on the
goroutine stack. If we run this with `./stacker 1000000` we'll
allocate more than is available and the Go runtime will move the
stack.

```go
package main

import (
	"fmt"
	"os"
	"strconv"
)

type Example struct {
	ID   int
	Name string
}

func stacker(count int) string {
	var result int
	for i := 0; i < count; i++ {
		temp := Example{ID: i * 2, Name: fmt.Sprintf("%d", result)}
		result += temp.ID
	}
	s := fmt.Sprintf("hello: %d", result)
	return s
}

func main() {
	args := os.Args
	if len(args) < 2 {
		panic("needs 1 arg")
	}
	count, err := strconv.Atoi(args[1])
	if err != nil {
		panic("arg needs to be a number")
	}

	s := stacker(count)
	fmt.Println(s)
}
```

Here's our `bpftrace` program:

```awk
#!/usr/bin/env bpftrace

uretprobe:./stacker:"main.stacker"
{
    printf("result: \"%s\"\n", str(reg("ax")));
}
```

But if we run `stacker` with a sufficiently large `count` while our
`uretprobe` is attached, it will crash!

```
$ ./stacker 1000000
runtime: unexpected return pc for main.stacker called from 0x7fffffffe000
stack: frame={sp:0xc000074ef0, fp:0xc000074f48} stack=[0xc000074000,0xc000075000)
...
```

Here's the full dump if you're into that kind of thing:

<details>

```
$ ./stacker 1000000
runtime: unexpected return pc for main.stacker called from 0x7fffffffe000
stack: frame={sp:0xc000074ef0, fp:0xc000074f48} stack=[0xc000074000,0xc000075000)
0x000000c000074df0:  0x0000000000000002  0x000000c000508100
0x000000c000074e00:  0x000000c000508000  0x00000000004672e0 <sync.(*Pool).pinSlow·dwrap·3+0x0000000000000000>
0x000000c000074e10:  0x0000000000557f58  0x000000c000074e08
0x000000c000074e20:  0x0000000000419860 <runtime.gcAssistAlloc.func1+0x0000000000000000>  0x000000c0000001a0
0x000000c000074e30:  0x0000000000010000  0x000000c000074eb8
0x000000c000074e40:  0x000000000040b305 <runtime.mallocgc+0x0000000000000125>  0x000000c0000001a0
0x000000c000074e50:  0x0000000000000002  0x000000c000074e88
0x000000c000074e60:  0x000000c000074e88  0x000000000047a06a <fmt.(*pp).free+0x00000000000000ca>
0x000000c000074e70:  0x0000000000522100  0x00000000004938e0
0x000000c000074e80:  0x000000c00007a820  0x000000c000074ee0
0x000000c000074e90:  0x000000000047a245 <fmt.Sprintf+0x0000000000000085>  0x000000c00007a820
0x000000c000074ea0:  0x000000c00012b230  0x000000000000000b
0x000000c000074eb0:  0x000000c0000001a0  0x000000c000074ee0
0x000000c000074ec0:  0x00000000004095e5 <runtime.convT64+0x0000000000000045>  0x0000000000000008
0x000000c000074ed0:  0x0000000000487ee0  0x000000c00007a800
0x000000c000074ee0:  0x000000c000074f38  0x0000000000480d7b <main.stacker+0x000000000000003b>
0x000000c000074ef0: <0x0000000644e0732a  0x0000000000000002
0x000000c000074f00:  0x000000c000074f28  0x0000000000000001
0x000000c000074f10:  0x0000000000000001  0x0000000644e0732a
0x000000c000074f20:  0x00000000000280fa  0x0000000000000000
0x000000c000074f30:  0x0000000000000000  0x000000c000074f70
0x000000c000074f40: !0x00007fffffffe000 >0x00000000000f4240
0x000000c000074f50:  0x0000000000000007  0x0000000000415d45 <runtime.gcenable+0x0000000000000085>
0x000000c000074f60:  0x00000000004873a0  0x000000c0000001a0
0x000000c000074f70:  0x000000c000074fd0  0x0000000000432047 <runtime.main+0x0000000000000227>
0x000000c000074f80:  0x000000c000022060  0x0000000000000000
0x000000c000074f90:  0x0000000000000000  0x0000000000000000
0x000000c000074fa0:  0x0100000000000000  0x0000000000000000
0x000000c000074fb0:  0x000000c0000001a0  0x0000000000432180 <runtime.main.func2+0x0000000000000000>
0x000000c000074fc0:  0x000000c000074fa6  0x000000c000074fb8
0x000000c000074fd0:  0x0000000000000000  0x000000000045ab01 <runtime.goexit+0x0000000000000001>
0x000000c000074fe0:  0x0000000000000000  0x0000000000000000
0x000000c000074ff0:  0x0000000000000000  0x0000000000000000
fatal error: unknown caller pc

runtime stack:
runtime.throw({0x4988ba, 0x516760})
        /usr/local/go/src/runtime/panic.go:1198 +0x71
runtime.gentraceback(0x400, 0x400, 0x80, 0x7f73bbffafff, 0x0, 0x0, 0x7fffffff, 0x7ffc46fe0e28, 0x7f73bbe23200, 0x0)
        /usr/local/go/src/runtime/traceback.go:274 +0x1956
runtime.scanstack(0xc0000001a0, 0xc000030698)
        /usr/local/go/src/runtime/mgcmark.go:748 +0x197
runtime.markroot.func1()
        /usr/local/go/src/runtime/mgcmark.go:232 +0xb1
runtime.markroot(0xc000030698, 0x14)
        /usr/local/go/src/runtime/mgcmark.go:205 +0x170
runtime.gcDrainN(0xc000030698, 0x10000)
        /usr/local/go/src/runtime/mgcmark.go:1134 +0x14b
runtime.gcAssistAlloc1(0xc0000001a0, 0xc000074b58)
        /usr/local/go/src/runtime/mgcmark.go:537 +0xef
runtime.gcAssistAlloc.func1()
        /usr/local/go/src/runtime/mgcmark.go:448 +0x25
runtime.systemstack()
        /usr/local/go/src/runtime/asm_amd64.s:383 +0x49

goroutine 1 [GC assist marking (scan)]:
runtime.systemstack_switch()
        /usr/local/go/src/runtime/asm_amd64.s:350 fp=0xc000074de8 sp=0xc000074de0 pc=0x458a20
runtime.gcAssistAlloc(0xc0000001a0)
        /usr/local/go/src/runtime/mgcmark.go:447 +0x18b fp=0xc000074e48 sp=0xc000074de8 pc=0x41974b
runtime.mallocgc(0x8, 0x487ee0, 0x0)
        /usr/local/go/src/runtime/malloc.go:959 +0x125 fp=0xc000074ec8 sp=0xc000074e48 pc=0x40b305
runtime.convT64(0x644e0732a)
        /usr/local/go/src/runtime/iface.go:364 +0x45 fp=0xc000074ef0 sp=0xc000074ec8 pc=0x4095e5
runtime: unexpected return pc for main.stacker called from 0x7fffffffe000
stack: frame={sp:0xc000074ef0, fp:0xc000074f48} stack=[0xc000074000,0xc000075000)
0x000000c000074df0:  0x0000000000000002  0x000000c000508100
0x000000c000074e00:  0x000000c000508000  0x00000000004672e0 <sync.(*Pool).pinSlow·dwrap·3+0x0000000000000000>
0x000000c000074e10:  0x0000000000557f58  0x000000c000074e08
0x000000c000074e20:  0x0000000000419860 <runtime.gcAssistAlloc.func1+0x0000000000000000>  0x000000c0000001a0
0x000000c000074e30:  0x0000000000010000  0x000000c000074eb8
0x000000c000074e40:  0x000000000040b305 <runtime.mallocgc+0x0000000000000125>  0x000000c0000001a0
0x000000c000074e50:  0x0000000000000002  0x000000c000074e88
0x000000c000074e60:  0x000000c000074e88  0x000000000047a06a <fmt.(*pp).free+0x00000000000000ca>
0x000000c000074e70:  0x0000000000522100  0x00000000004938e0
0x000000c000074e80:  0x000000c00007a820  0x000000c000074ee0
0x000000c000074e90:  0x000000000047a245 <fmt.Sprintf+0x0000000000000085>  0x000000c00007a820
0x000000c000074ea0:  0x000000c00012b230  0x000000000000000b
0x000000c000074eb0:  0x000000c0000001a0  0x000000c000074ee0
0x000000c000074ec0:  0x00000000004095e5 <runtime.convT64+0x0000000000000045>  0x0000000000000008
0x000000c000074ed0:  0x0000000000487ee0  0x000000c00007a800
0x000000c000074ee0:  0x000000c000074f38  0x0000000000480d7b <main.stacker+0x000000000000003b>
0x000000c000074ef0: <0x0000000644e0732a  0x0000000000000002
0x000000c000074f00:  0x000000c000074f28  0x0000000000000001
0x000000c000074f10:  0x0000000000000001  0x0000000644e0732a
0x000000c000074f20:  0x00000000000280fa  0x0000000000000000
0x000000c000074f30:  0x0000000000000000  0x000000c000074f70
0x000000c000074f40: !0x00007fffffffe000 >0x00000000000f4240
0x000000c000074f50:  0x0000000000000007  0x0000000000415d45 <runtime.gcenable+0x0000000000000085>
0x000000c000074f60:  0x00000000004873a0  0x000000c0000001a0
0x000000c000074f70:  0x000000c000074fd0  0x0000000000432047 <runtime.main+0x0000000000000227>
0x000000c000074f80:  0x000000c000022060  0x0000000000000000
0x000000c000074f90:  0x0000000000000000  0x0000000000000000
0x000000c000074fa0:  0x0100000000000000  0x0000000000000000
0x000000c000074fb0:  0x000000c0000001a0  0x0000000000432180 <runtime.main.func2+0x0000000000000000>
0x000000c000074fc0:  0x000000c000074fa6  0x000000c000074fb8
0x000000c000074fd0:  0x0000000000000000  0x000000000045ab01 <runtime.goexit+0x0000000000000001>
0x000000c000074fe0:  0x0000000000000000  0x0000000000000000
0x000000c000074ff0:  0x0000000000000000  0x0000000000000000
main.stacker(0xf4240)
        /home/tim/stacker/main.go:17 +0x3b fp=0xc000074f48 sp=0xc000074ef0 pc=0x480d7b
```

</details>

Instead, we still have to use the `uprobe` + offset technique we saw
above. This `bpftrace` program works safely, but the address offset is
going to vary depending on which version of Go you're using:

```awk
#!/usr/bin/env bpftrace

uprobe:./stacker:"main.stacker"+213
{
    printf("result: \"%s\"\n", str(reg("ax")));
}
```

This problem is probably not going to be fixed from the Go runtime
side, because the relocatable stack is baked into the whole memory
model for goroutines. But with `uprobes` and a little inventiveness,
you can get most of the same functionality.

---
categories:
- development
- rust
- wasm
date: 2021-09-30T12:00:00Z
title: "An Embedded WASM Shell"
slug: embedded-wasm-shell
---

If I go back far enough, it's clear my professional career in tech
started with the realization that AutoCAD's command line interface was
in fact a _shell_. It didn't just accept instructions, but you could
write little programs in this "weird language" called Lisp and it
would make calculations based on your drawing or even make changes to
the drawing[^1]. I started with automating repetitive work, and then
one day a forward-thinking architect I worked with asked if I could
write a program that would make accurate construction bid
estimates. The first project built came within 5% of the software
estimated budget, and it's been a roughly 20 year trip from there to
writing blog posts about WASM for you today.

But the important part of this trip down memory lane is the notion
that you can have software that includes a constrained embedded
programming environment, and the power this provides a skilled user to
fit the software to their purpose. A former colleague [Sam
Wilson](https://twitter.com/numbsafari) gave a great talk at the
Philadelphia DevOps meetup a few years ago[^2] where he called this
idea "coding in production." The key to making this work is that the
interface should be exploratory, as one gets with a REPL or SQL
console, and that it should be properly constrained for safety.

This all came to mind again recently while working on an application
with a lot of internal state, where I wanted to expose a REPL to
operators so they could debug that state "live". For various reasons,
I want to be able to assert to the owner of the data that the shell
user can't arbitrarily damage the data[^3]. So I've built the
beginnings of an embeddable Scheme interpreter in Rust, compiled to a
Web Assembly (WASM) module hosted via Wasmtime.

Most of the use cases I've seen for WASM boil down to either (1) "I
don't want to write JavaScript for the web" or (2) "I want to host
other people's untrusted code in a PaaS-like environment", which are
both awesome use cases. But this means that a lot of the example code
in the documentation handwaves over the communication between the host
application and the WASM guest, because either you're leaning on DOM
bindgen libraries or exposing a narrow system interface to the guest
like allowing it access to specific file handles. In particular, I
struggled with figuring out how a guest written in Rust was supposed
to set up linear memory and make host function calls.

I've published the code below as a repository with commits for each
step at [tgross/wasm-shell-example].

> Allergy warning: please note that this use case requires the
> `unsafe` keyword in the guest application. The host application has
> no use of `unsafe` in the application code, but of course if you dig
> down far enough into the wasmtime library you'll find it there as
> well. In any case, this code was extracted from the project I'm
> working on and is intended for educational purposes and not any
> particular use.

Because my Scheme interpreter is incomplete and not the point of this
post, we'll start with the dumbest possible shell that just echos
whatever you input:

```rust
fn main() {
    loop {
        let mut user_input = String::new();
        io::stdin()
            .read_line(&mut user_input)
            .expect("error reading in user input");
        let result = eval(&user_input);
        println!("{:?}", result);
    }
}

fn eval(input: &str) -> &str {
    input
}
```

We'll set up a Cargo workspace with an empty host application, and
exclude the shell from the workspace so that we can compile it to a
separate target via a Makefile[^4]. Then we compile the shell with
[`cargo wasi build`] and get a `.wasm` target. This is commit [`0e7dff6`].

Next we'll build the host. Most of this is right out of the [Wasmtime
docs on embedding in Rust], but I want to point out that we're using
WASI to let the guest inherit stdin/stdout from the host:

```rust
let wasi = WasiCtxBuilder::new().inherit_stdio().build();
let mut store = Store::new(&engine, wasi);
```

With `cargo run` we can interact with the shell directly in our
terminal. This is commit [`c1e34bb`], but it's not very interesting.

Instead, let's have the host expose a Unix Domain Socket, and have
each connection on this socket start its own shell. This gives us an
example of how the host program can restrict the guest. We could allow
remote access over TLS with authentication, we could rate-limit
connections or data transfer, or we could allow certain users access
to more WASM "fuel" than others. So long as we implement the
`std::io::{Read, Write}` traits, the guest shell doesn't need to know
(and indeed _shouldn't know_) these details.

For each connection, we'll spawn a thread and hand it the new stream
and reference-counted copies of the WASM engine, our compile module,
the linker with our functions (we'll come back to those in a moment),
and the application state:

```rust
let linker = Arc::new(linker);
let state = Arc::new(Mutex::new(State::new()));
let listener = UnixListener::bind(bind_path)?;

for stream in listener.incoming() {
    match stream {
        Ok(stream) => {
            let state = state.clone();
            let engine = engine.clone();
            let module = module.clone();
            let linker = linker.clone();
            thread::spawn(move || handle_client(stream, &engine, &module, &linker, &state));
        }
        Err(_) => {
            eprintln!("connection failed");
            break;
        }
    }
}
```

In the handler, we end up needing to clone the stream twice: once to
split it into a reader and writer stream (for stdin and stdout), and
once more to have an error channel so the host can send in-band error
messages to the client even if the guest shell exits unexpectedly.

Next we present the two streams as `WasiFile` to the WASI context, and
spawn a new `wasmtime::Store` from this context and the application
state:

```rust
let wasi = WasiCtxBuilder::new()
    .stdin(Box::new(ReadPipe::new(stream)) as Box<dyn WasiFile>)
    .stdout(Box::new(WritePipe::new(write_stream)) as Box<dyn WasiFile>)
    .build();

let mut store = Store::new(
    &engine,
    StoreData {
        state: state,
        wasi: wasi,
    },
);
```

And finally we instantiate our WASM instance with the shell. Because
we've built a binary (i.e. something with a `main`), we'll call the
`_start` function. This is commit [`fafc0f3`].

```rust
let mut run_interpreter = move || -> Result<(), Trap> {
    let instance = linker.instantiate(&mut store, module)?;
    let run = instance.get_typed_func::<(), (), _>(&mut store, "_start")?;
    run.call(&mut store, ())
};

if let Err(e) = run_interpreter() {
    if let Err(e) = write!(&mut err_stream, "{}", e) {
        eprintln!("{}", e);
    }
    return;
};
```

At this point we can `cargo run` and connect to the socket file from
another terminal with `socat - UNIX-CONNECT:/tmp/wasm-shell.sock`. But
our shell still doesn't _do_ anything other than echo back our
results. Let's change that.

## Updating Host State from the Guest

Earlier we'd glossed over the application state, so let's populate a
`State` and a separate `StoreData` that contains the state and the
`WasiCtx` for the WASM engine. The host application will use this same
object to manipulate state from its side. This could even include a
reference to your database connection if our application had one.

```rust
struct State {
    counts: Vec<i32>,
}

struct StoreData<'a> {
    state: &'a Arc<Mutex<State>>,
    wasi: WasiCtx,
}
```

Our state is a vector of integers, and the two functions we're going
to expose to the shell are `add` to push another number onto the
vector, and `sum` to total all the numbers we've seen so far. I'm
intentionally punting on more complex objects like strings for the
moment, but we'll come back to that.

```rust
impl State {
    fn add(&mut self, val: i32) {
        self.counts.push(val);
    }

    fn sum(&self) -> i32 {
        self.counts.iter().fold(0, |mut sum, &x| {
            sum += x;
            sum
        })
    }
}
```

Wrapping one of these functions has some important details to call
out. The first string is the name of the module our guest will import,
and the second string is the name we'll expose to the guest shell. The
signature of the closure is a [`wasmtime::IntoFunc`] and all the
arguments must be compatible with WebAssembly types. So for example,
you can't pass a `usize` or `u8` here, nor can you return a tuple or
struct. When we want to manipulate the state, we call either `data()`
or `data_mut()` to get a reference (or mutable reference) to the
caller's `Store`, and then take the mutex to finally get our `State`
methods.

```rust
linker.func_wrap(
    "host",
    "host_add",
    |mut caller: Caller<'_, StoreData>, param: i32| {
        caller.data_mut().state.lock().unwrap().add(param);
    },
)?;
```

How do we call these functions from our shell? The Wasmtime [import
host functionality] docs are helpful here. Note that calling these
functions is always `unsafe`:

```rust
#[link(wasm_import_module = "host")]
extern "C" {
    fn host_add(count: i32);
    fn host_sum() -> i32;
}
```

Lastly, we'll update our `eval` function in the guest to parse our
inputs and call the functions. Normally we'd probably want to use a
real command-line parsing library, but this will do for now.

```rust
fn eval(input: &str) -> String {
    let parsed: Vec<_> = input.trim_end().trim_start().split(' ').collect();
    match parsed.get(0) {
        Some(&"sum") => unsafe { format!("{}", host_sum()) },
        Some(&"add") => match parsed.get(1) {
            Some(next) => match str::parse(next) {
                Ok(i) => {
                    unsafe { host_add(i); }
                    "ok".to_string()
                }
                _ => { ... }
            },
            _ => { ... }
        }
    }
}
```

At this point we should be able to run the application, and connect
with two different instances of socat. Each connection should be able
to see the changes written to the state by the other, so if we `add 2`
in one and `add 3` in the other, `sum` will now return `5` in
both. This is commit [`a226910`].

## Working Around Interface Types

To use functions that pass arguments or return values that are
something other than integers and floats, we need [WebAssembly
Interface Types]. Unfortunately these have not yet been standardized
and shipped! This would put a damper on our ambitions to have a shell,
but we can work around this by using WASM linear memory.

Effectively what we're going to do is make a syscall-like interface
between our guest and host. The guest will write to a buffer, and then
call a host function passing a pointer (or rather, an offset in the
WASM linear memory) and length for each parameter and for the return
value. The host will get the result and write the value back to return
buffer and return the length of the data written to the caller.

We'll be using "safe" `wasmtime::Memory` interfaces on the host side
that copy the data out before working on it, and on the guest side
we're single threaded and waiting on the return from the host
function. So we don't need to worry about the guest messing with the
data while we're reading it. (And hopefully interface types ship
before threads!)

That being said, I managed to segfault the guest a few dozen times
before finally finding Radu Matei's excellent [_Practical Guide to
WASM Memory_]. The control flow we have here is reverse from Matei's
post, because the guest is deciding what to allocate. But as it turns
out this largely gets implemented in the same way. We want these two
functions in the guest:

```rust
fn alloc(len: usize) -> *mut u8 {
    let mut buf = vec![0u8; len];
    let ptr = buf.as_mut_ptr();
    std::mem::forget(buf);
    ptr
}

unsafe fn dealloc(ptr: *mut u8, len: usize) {
    let _buf = Vec::from_raw_parts(ptr, 0, len);
    std::mem::drop(_buf);
}
```

If we were exporting these functions from the guest these would need
to be `extern "C"`, but in this workflow we'll keep all the `unsafe`
code inside the guest. When the guest prepares a buffer for the host
(either a parameter or space for the result), it calls `alloc`. That
`alloc` function "forgets" about the buffer we allocate without
dropping it. If we skip this, the buffer will get reclaimed and the
host will get garbage data (which it will safely reject when it tries
to parse it into a string). But the error message we write in the
return buffer is also corrupt in the same way, and the guest crashes
("traps", in WASM parlance). This workflow also means we need to clean
up the buffer manually with `dealloc`. In `dealloc` we read the buffer
pointed to by the pointer, and then drop it.

We can put this all together to pass a string to the `host_kv_get`
function. We allocate a buffer for the key, and copy the key into
it. We also need to allocate the buffer for the response. Then we pass
the pointers and lengths of both buffers into the `host_kv_get`
function that we've imported. The return value of `host_kv_get` will
be the number of bytes written into the response buffer.

```rust
fn eval_kv_get(key: &str) -> String {
    let key_len = key.len();
    let res;

    unsafe {
        let key_ptr = alloc(key.len());
        std::ptr::copy(key.as_ptr(), key_ptr, key_len);

        let res_ptr = alloc(MAX_RESPONSE_LENGTH);

        let _res_len = host_kv_get(
            key_ptr as u32,
            key_len as u32,
            res_ptr as u32,
            MAX_RESPONSE_LENGTH as u32,
        );

        let res_len = _res_len.try_into().unwrap();
        res = read_results(res_ptr, res_len);

        // free our forgotten memory for the key; the from_utf8 will
        // free the response buffer
        dealloc(key_ptr, key_len);
    }
    match std::str::from_utf8(&res) {
        Ok(s) => s.to_string(),
        Err(err) => format!("error parsing results as string: {:?}", err),
    }
}
```

The `eval_key_set` function is almost identical, but with an extra
buffer for the value we want to set. The guest side of this work is
commit [`c84c596`].

## Reading Memory From the Host

As we saw earlier the [`wasmtime::FuncWrap`] expects a closure and if
we want to access memory the first parameter of that closure is a
[`wasmtime::Caller`]. Getting the memory and accessing the store in
the correct order is a little fussy if you want to both read and write
to memory in the same function (as we do here), because writing will
need a mutable borrow. I've elided some error handling here but you
can see the full code listing in commit [`f95d398`]. Note that we're
looking for the export named "memory", which is what the `wasm32-wasi`
target [exports by default].

```rust
linker.func_wrap(
    "host", "host_kv_get",
    |mut caller: Caller<'_, StoreData>,
     key_ptr: u32, key_len: u32,
     res_ptr: u32, res_len: u32|
     -> u32 {
        let mem = match caller.get_export(&"memory"){ ... }
        let store = caller.as_context();
        let result = kv_get(mem, &store, key_ptr, key_len, res_ptr, res_len);

        // now that we're done with our borrow, upgrade to mutable
        let mut store = caller.as_context_mut();
        match result {
            Ok(response) => {
                return write_response(mem, &mut store, res_ptr, res_len, response)
                    .map_err(|err| eprintln!("{}", err))
                    .unwrap_or(0);
            }
            Err(err) => { ... }
        }
    },
)?;
```

This wrapper is calling into functions that return a `Result` and then
it's responsible for writing that response back. The `kv_get`
implementation can be fairly slim:

```rust
fn kv_get(
    mem: Memory, store: &StoreContext<StoreData>,
    key_ptr: u32, key_len: u32,
    res_ptr: u32, res_len: u32,
) -> Result<String> {
    let key = read_parameter(mem, &store, key_ptr, key_len)?;
    validate_wasm_param(res_ptr, res_len)?;
    let max_len: usize = res_len.try_into().unwrap_or(1024);

    let map = &store.data().state.lock().unwrap().map;
    let mut response = map.get(&key).ok_or(anyhow!("no such key"))?.to_string();
    response.truncate(max_len);
    Ok(response)
}
```

And finally we have a couple of helper functions for reading and
writing the memory:

```rust
fn read_parameter(
    mem: Memory,
    store: &StoreContext<StoreData>,
    ptr: u32,
    len: u32,
) -> Result<String> {
    validate_wasm_param(ptr, len)?;
    let mut buf = vec![0u8; len as usize];
    mem.read(&store, ptr.try_into()?, &mut buf)?;
    Ok(std::str::from_utf8(&buf)?.to_string())
}

fn write_response(
    mem: Memory,
    store: &mut StoreContextMut<StoreData>,
    ptr: u32,
    max_len: u32,
    mut response: String,
) -> Result<u32> {
    response.truncate(max_len.try_into()?);
    mem.write(store, ptr.try_into()?, response.as_bytes())?;
    Ok(response.len() as u32)
}
```

This is all wired up in commit [`f95d398`]. Now we can `cargo run` and
connect to the shell, and do `set :key :val` in one shell and retrieve
that value from `get :key` in another shell.

## Wrapping Up

So how practical is all of this? I haven't yet explored async
functions, which is fine for this use case but could be a performance
issue for guests that are doing a lot of IO. There's definitely enough
to build a real application here. But expect to have to make some
investment in the infrastructure around host/guest communication.


[^1]: The command window doubled as an AutoLISP REPL, but you could
    of course also load programs from files on disk, including while
    starting up AutoCAD. I have a vague memory that the entire drawing
    could even be exported as a s-expression in text format, but a
    quick look at the DXF format spec says my memory is faulty. Was
    there another way to do this that I've forgotten?
[^2]: Sadly it's not online anywhere.
[^3]: Not the least of which because I'll be the only operator for the
    foreseeable future and I'm obviously an idiot.
[^4]: It looks like
    [cargo/#9406](https://github.com/rust-lang/cargo/issues/9406) will
    make this unnecessary.


[tgross/wasm-shell-example]: https://github.com/tgross/wasm-shell-example
[`cargo wasi build`]: https://github.com/bytecodealliance/cargo-wasi
[Wasmtime docs on embedding in Rust]: https://docs.wasmtime.dev/examples-rust-hello-world.html
[WebAssembly Interface Types]: https://github.com/webassembly/interface-types
[_Practical Guide to WASM Memory_]: https://radu-matei.com/blog/practical-guide-to-wasm-memory/
[`wasmtime::IntoFunc`]: https://docs.rs/wasmtime/0.18.0/wasmtime/struct.Func.html#method.wrap
[import host functionality]: https://docs.wasmtime.dev/wasm-rust.html#importing-host-functionality
[`wasmtime::FuncWrap`]: https://docs.rs/wasmtime/0.30.0/wasmtime/struct.Func.html#method.wrap
[`wasmtime::Caller`]: https://docs.rs/wasmtime/0.30.0/wasmtime/struct.Caller.html#
[exports by default]: https://docs.wasmtime.dev/wasm-rust.html#exporting-rust-functionality
[`0e7dff6`]: https://github.com/tgross/wasm-shell-example/commit/0e7dff66bf2537f4da0254a7683922a031731cf4
[`c1e34bb`]: https://github.com/tgross/wasm-shell-example/commit/c1e34bb804d81932d9e9dc1c92fc360e576362d0
[`fafc0f3`]: https://github.com/tgross/wasm-shell-example/commit/fafc0f316ad30ef318019b8f7253dd896a920ea4
[`a226910`]: https://github.com/tgross/wasm-shell-example/commit/a226910c2201500e4108b7c6fa851eee9ed1f8dc
[`c84c596`]: https://github.com/tgross/wasm-shell-example/commit/c84c5960726bdaf4e02ae25541d2a33a378adb51
[`f95d398`]: https://github.com/tgross/wasm-shell-example/commit/f95d3980b7d77a446d1b5c23cf466af33a0792d7

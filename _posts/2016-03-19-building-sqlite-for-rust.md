---
layout: post
title: Building sqlite for rust
category: rust
tweet: Rust and Cargo get this stuff right!

---

I've been playing around with Rust a bit lately and needed to build something with an embedded database, so I reached for SQLite. I need to build SQLite with some specific features enabled and that's hard to guarantee with system packages cross-platform. This gave me a chance to try out building a Rust project linked with some custom C code. The overall direction I'm taking here is largely coming from [this thread](https://users.rust-lang.org/t/linking-with-custom-c-library/637/4) and the Cargo [build script](http://doc.crates.io/build-script.html#case-study-building-some-native-code) page. I'm using [rusqlite](https://github.com/jgallagher/rusqlite) for the SQLite bindings, so I'll need to build that as well.

## Project outline

The other nice thing I got to try out here is how to build a sensible project structure for a project that might mix open source and private code. Cargo has some very minimal expectations about the source code directory, but doesn't dictate much past that. So unlike that *other* language [(*ahem*)](http://0x74696d.com/posts/go-get-considered-harmful) Rust is pretty chill about letting you decide what works for your project and organization. How this reflects on the culture of those two languages is left as an exercise for the reader.


~~~
$ tree /src/tgross/demo
.
├── build.rs
├── Cargo.toml
├── .git/
├── src/
│   └── main.rs
└── target/

$ tree /src/jgallagher/rusqlite
.
├── Cargo.toml
├── .git/
├── libsqlite3-sys/
│   ├── build.rs
│   └── Cargo.toml
│   └── src/
├── src/
│   └── main.rs
└── target/
~~~

In this directory tree I've got my own code namespaced under `tgross/` and my library code in the `jgallagher/rusqlite` directory. The `rusqlite` developers in turn decided to "vendor" their `libsqlite3-sys` crate because it's really just there to create bindings and doesn't stand on its own. I could just as easily take `rusqlite` and vendor it as a Git submodule or subtree at an arbitrary location within my own project's directory structure. Rather than pretending that our packaging and dependency tree can be described entirely by `import`s in our source code, Rust gives us Cargo, and we can give Cargo search paths for libraries.

This is really fucking important if you want to have repeatable builds and to keep all your hair during development. It means that source control and the on-disk representation of source code is decoupled from the import paths in the source code. If every scrap of code you write and pull from third parties exists in a giant monorepo (like Google does it), maybe you won't notice. But this means I can start development by pulling from GitHub or [crates.io](https://crates.io/), fork a local copy of a dependency for debugging, or mirror a third-party repository in my CI/CD workflow. (DevOps pro-tip: this means you can still ship software to customers when GitHub is down.) And all of that happens without running around my source tree rewriting imports, or worrying about tree-shaking, or fiddling with environment variables. *The Rust developers got this shit right.*

Ok, rant over. Deep breaths...

## Cargo.toml

This is just the "hello world" of `rusqlite`, so our demonstration application will be [the example code from the rusqlite README](https://github.com/jgallagher/rusqlite/blob/master/README.md). Here's our demo app's Cargo.toml:

~~~toml
[package]
name = "demo"
version = "0.1.0"
authors = ["Tim Gross <tim@0x74696d.com>"]
build = "build.rs"
links = "libsqlite"

[dependencies]
time = "~0.1.0"

[dependencies.rusqlite]
path = "/src/jgallagher/rusqlite"

[build-dependencies]
gcc = "0.3"
~~~

Note that I've got four different dependencies here and each one is being added in a different way. The most straightforward is the `time` crate, which our demonstration app uses to get the current time when inserting a row. We've pinned it to a specific version with the `~` flag, which means we'll accept patch version updates but not minor version increases (in the semver sense). When we build, Cargo will fetch this dependency from crates.io, compile it, and then cache the output of that compilation in our target directory for linking down the road.

We also have a separate `[dependencies.rusqlite]` section here, where we've specified a path. This path will be an on-disk location where Cargo will try to find the dependency, rather than going out to the Internet for it. This is convenient if I want to work up a patch of `rusqlite` or if I've got another private project that I want to link in here without fetching it from GitHub (i.e. from the mirror of repos on my CI/CD system). We can also pass feature flags or other compiler options to the dependency when we have it in its own section like this. Another option is to just have a `path` field under `[package]` and have Cargo search there first. But if you have a whole lot of code within those paths (as I do with a fairly flat `/src/tgross/` directory), then you're going to be risking annoying collisions.

Next we have `gcc`, which is marked under `[build-dependencies]`. This feature lets you fetch crates for purposes of the build process (or for testing with `[dev-dependencies]`), but these crates won't be linked into your final library or executable binary output. We're going to use the [`gcc` crate](http://alexcrichton.com/gcc-rs/gcc/index.html) to assist us with building SQLite.

Lastly and perhaps less obviously, we have a `links` and `build` section under `[package]`. This is how we're going to tell Cargo that we have to build and link an external library.

## build.rs

We still need to tell Cargo how to actually build SQLite, and is pretty straightforward with the `gcc` crate. In our [`build.rs` script](http://doc.crates.io/build-script.html) we just need to pass the appropriate arguments to the gcc methods and we'll get the expected output.

~~~rust
extern crate gcc;

fn main() {
gcc::Config::new()
    .define("SQLITE_ENABLE_FTS5", Some("1"))
    .define("SQLITE_ENABLE_RTREE", Some("1"))
    .define("SQLITE_ENABLE_JSON1", Some("1"))
    .define("SQLITE_ENABLE_DBSTAT_VTAB", Some("1"))
    .define("SQLITE_ENABLE_EXPLAIN_COMMENTS", Some("1"))
    .file("/src/sqlite/src/sqlite3.c")
    .compile("libsqlite3.a");
}
~~~

This is the equivalent of doing:

~~~bash
gcc -DSQLITE_ENABLE_FTS5=1 \
	-DSQLITE_ENABLE_RTREE=1 \
	-DSQLITE_ENABLE_JSON1=1 \
	-DSQLITE_ENABLE_DBSTAT_VTAB=1 \
	-DSQLITE_ENABLE_EXPLAIN_COMMENTS=1 \
	-c src/sqlite3.c \
	-lpthread -ldl \
	-o libsqlite3.a

~~~

Note that the linked pthread and ld libs will be provided as part of our standard rust build. Optimization level and whether to include debug symbols will be set according to the Cargo build, but these can be overridden (see the [`gcc::Config`](http://alexcrichton.com/gcc-rs/gcc/struct.Config.html#method.opt_level) docs).

Also note here that we're hard-coding the path to the [SQLite source amalgamation file](https://www.sqlite.org/amalgamation.html), which kinda sucks. The `libsqlite3-sys` crate handles this by taking an environment variable, or we could just vendor the `sqlite3.c` source and header file alongside our code. If anyone knows a good workaround I'd be interested to hear about it.

In any case, now we're ready to build!

~~~bash
$ cargo build
cargo build
    Compiling bitflags v0.1.1
    Compiling winapi v0.2.6
    Compiling libc v0.2.8
    Compiling pkg-config v0.3.8
    Compiling winapi-build v0.1.1
    Compiling gcc v0.3.25
    Compiling kernel32-sys v0.2.1
    Compiling libsqlite3-sys v0.4.0 (file:///src/tgross/demo)
    Compiling time v0.1.34
    Compiling demo v0.1.0 (file:///src/tgross/demo)
    Compiling rusqlite v0.6.0 (file:///src/tgross/demo)

$ ldd target/debug/demo
    linux-vdso.so.1 (0x00007ffdf7abe000)
    libdl.so.2 => /lib/x86_64-linux-gnu/libdl.so.2 (0x00007f9404...
    libpthread.so.0 => /lib/x86_64-linux-gnu/libpthread.so.0 (0x...
    libgcc_s.so.1 => /lib/x86_64-linux-gnu/libgcc_s.so.1 (0x0000...
    libc.so.6 => /lib/x86_64-linux-gnu/libc.so.6 (0x00007f940385...
    /lib64/ld-linux-x86-64.so.2 (0x00007f94045b9000)
    libm.so.6 => /lib/x86_64-linux-gnu/libm.so.6 (0x00007f940355...

$ ./target/debug/demo
Found person Person { id: 1, name: "Steven",
time_created: Timespec { sec: 1458435347, nsec: 0 }, data: None }
~~~

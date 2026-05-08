# Compiling into executable programs

This guide explains a method for running the EEA program using Dune, the OCaml build system, in a Windows operating system. One can use their own method.

## Prerequisites

- Working Ubuntu/WSL
- Opam — The OCaml package/virtual-env manager
- OCaml — The target language for extraction
- Dune — The OCaml build system
- `F*` with compatible Z3

WSL is a software that runs Ubuntu on Windows for a consistent build toolchain.

We use the proof-oriented language `F*` to verify the algorithm and then compile the verified code into fast native executables in the target language OCaml. OCaml unifies functional, imperative, and object-oriented programming under an ML-like type system.

Opam is the package/virtual-env manager of OCaml; we use it to create isolated compiler "switches" and to install OCaml, Dune, and required libraries.

Dune is a build system for OCaml; it is used for building, running, and testing the extracted code and its dependencies.

### Installing the OCaml suite

If you don't have opam yet:

```
sudo apt-get update
sudo apt-get install -y opam m4 pkg-config
```

Then initialize opam:

```
opam init -y --disable-sandboxing
eval "$(opam env)"
```

in which:

- `opam init -y --disable-sandboxing`
  - `-y`: non-interactive; auto-answers "yes" to prompts.
  - `--disable-sandboxing` turns off build isolation.
- `eval "$(opam env)"`
  - Runs the shell commands that `opam env` prints to update your current shell, so the selected OCaml switch is immediately active.

Now, install the core packages:

```
opam install -y ocaml dune zarith yojson
eval "$(opam env)"
```

## Installing `F*`

A simple way to install `F*` is using opam:

```
opam install fstar
```

Alternative methods are available in the `F*` installation manual at https://github.com/FStarLang/FStar.

## Verifying in `F*` and extracting to OCaml

First verify the code; this step will be done automatically when extracting.

```
fstar.exe EEA.fst EEA.Prop.fst EEA.Verify.fst
```

Create a folder for output.

```
mkdir -p out
```

Extract `F*` code to OCaml.

```
fstar.exe --codegen OCaml --extract_module EEA --odir out \
  EEA.fst EEA.Prop.fst EEA.Verify.fst
```

Copy the necessary file (`Prims.ml` — every extracted OCaml module `open prims` and relies on the OCaml translations of `F*` primitives) into `/out`.

```
cp "$(fstar.exe --print_search_path | tr ':' '\n' | grep '/ulib' | head -n1)/ml/prims.ml" out/Prims.ml
```

Now you should have at least:

```
out/EEA.ml
out/Prims.ml
```

If you encounter issues in the last step, you can manually copy it from `/ulib/ml/Prims.ml` or `/ulib/ml/app/Prims.ml` in the root folder of `F*`.

Enter the folder `out`.

```
cd out
```

## Executing the program

Create a runner to execute the program. A sample runner can be created by entering the following in the command line:

```
cat > main.ml <<'OCAML'
open EEA
let () =
  let r = egcd (Z.of_int 39324666764520) (Z.of_int 2455312325433000) in
  Printf.printf "g=%s, x=%s, y=%s\n"
    (Z.to_string r.g) (Z.to_string r.x) (Z.to_string r.y)
OCAML
```

You can adjust the numbers inside `egcd (Z.of_int ...) (Z.of_int ...)`. This step can also be done manually by appending it to the end of `EEA.ml`.

Now, to create the Dune project file one can simply copy and paste the following block to the command line:

```
cat > dune-project <<'EOF'
(lang dune 3.9)
(name eea_demo)
EOF
```

where `(lang dune 3.9)` declares the Dune file version and `(name eea_demo)` names the project.

Create the Dune file.

```
cat > dune <<'EOF'
(executable
 (name main)
 (libraries zarith yojson ppx_deriving.runtime ppx_deriving_yojson)
 (preprocess (pps ppx_deriving.show ppx_deriving_yojson)))
EOF
```

Here we have:

- `libraries`
  - `zarith` — useful when code uses big ints.
  - `yojson` — JSON parsing/printing library.
  - `ppx_deriving.runtime` — small helpers needed at runtime by code generated via `ppx_deriving`.
  - `ppx_deriving_yojson` — provides JSON encode/decode helpers that the deriver emits.
- `preprocess (pps ...)`
  - `ppx_deriving.show` expands `[@@deriving show]` into pretty-printers (`show`, `pp`).
  - `ppx_deriving_yojson` expands `[@@deriving yojson]` into `to_yojson`/`of_yojson`.

If `[@@deriving ...]` is not used in any `.ml` file, both `preprocess` entries can be dropped. However, since this annotation is found in `Prims.ml`, they are needed here.

Finally, build and run the program.

```
dune clean
dune exec ./main.exe
```

### Troubleshooting PPX build failures

If the build fails due to a PPX issue, either install the required packages, or patch `Prims.ml` to remove the annotations:

```
cp Prims.ml Prims.ml.bak
sed -i -E 's/\[\@\@deriving[[:space:]]+show\]//g' Prims.ml
sed -i -E 's/\[\@\@deriving[[:space:]]+yojson\]//g' Prims.ml

cat > _yojson_stub.ml <<'OCAML'
(* --- Standalone build stubs (no PPX needed) --- *)
let tmp_to_yojson (s:string) : Yojson.Safe.t = `String s
let tmp_of_yojson (j:Yojson.Safe.t) =
  match j with `String s -> Ok s | _ -> Error "expected string"
let string_of_yojson (j:Yojson.Safe.t) =
  match j with `String s -> Ok s | _ -> Error "expected string"
let yojson_of_string (s:string) : Yojson.Safe.t = `String s
(* ------------------------------------------------ *)
OCAML
cat _yojson_stub.ml Prims.ml > Prims.ml.patched && mv Prims.ml.patched Prims.ml
rm _yojson_stub.ml
```

Alternatively, simplify the `dune` file to ignore all warnings:

```
(executable
 (name main)
 (libraries zarith yojson)
 (flags (:standard -w -8-27-32-39 -warn-error -a)))
```

## Output

If everything works correctly, the output after execution should be:

```
g=120, x=3867261527956, y=-61938666337
```

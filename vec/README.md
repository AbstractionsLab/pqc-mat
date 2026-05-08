# Verified implementations in F*

This repository provides an introductory tutorial to the use of [F*](https://fstar-lang.org/), a proof-oriented programming language, for generating verified implementations of cryptographic functions.

This work was carried out by an MSc mathematics student during an internship with the company.

The worked example is the [Extended Euclidean Algorithm](https://en.wikipedia.org/wiki/Extended_Euclidean_algorithm) (EEA) — a simple algorithm grounded in elementary number theory that underpins many cryptographic primitives (e.g., modular multiplicative inverses for RSA). 

Roughly, the verified code generation process can be summed up as follows:

1. Specify the algorithm in `F*` along with expected pre/post-conditions 
2. Prove termination and correctness w.r.t. the post-conditions assisted by the built-in SMT solver
3. Automatically extract verified executable code in the OCaml programming language from the EEA specification.
4. Run the generated code.

## Getting started

This folder hosts:

- A [compilation guide](./compilation-guide.md) that explains how to set up the toolchain (F*, OCaml, Dune) and run the verified EEA implementation.
- The [source code of the EEA](./src/EEA/) specifications in F*.
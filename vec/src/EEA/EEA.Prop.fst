module EEA.Prop
open FStar.Mul
open EEA

type bezout = EEA.bezout

(* d divides n  means there exists /k. n == k*d *)
let divides (d:int) (n:int) : Type =
  exists (k:int). n == k * d

(* gcd predicate by divisibility *)
let is_gcd (g:int) (a:int) (b:int) : Type =
  g >= 0 /\
  divides g a /\
  divides g b /\
  (forall (d:int). divides d a /\ divides d b ==> divides d g)

(* Bezout identity for a record r on inputs (a,b) *)
let is_bezout_identity (r:bezout) (a:int) (b:int) : Type =
  r.x * a + r.y * b == r.g

(* Full correctness bundle *)
let eea_correctness_conditions (r:bezout) (a:int) (b:int) : Type =
  is_bezout_identity r a b /\ is_gcd r.g a b

(* Lifting coefficients from (b,r) to (a,b).
  require a == q*b + r  *)
val bezout_lift :
  a:int -> b:int -> q:int -> r:int ->
  x':int -> y':int -> g:int ->
  Lemma
    (requires (a == q * b + r /\ (x' * b + y' * r == g)))
    (ensures  (y' * a + (x' - q * y') * b == g))
let bezout_lift a b q r x' y' g = ()

(* Base case for (a,0): code returns (x0,y0)=(1,0) if a>=0 else (-1,0). *)
val bezout_bc :
  a:int ->
  Lemma (ensures (is_bezout_identity (EEA.egcd a 0) a 0))

let bezout_bc a =
  // This reduces EEA.egcd a 0 by its definition in EEA.fst:
  if a >= 0 then
    // egcd a 0 = {g=a; x=1; y=0}  then  1*a + 0*0 == a
    ()
  else
    // egcd a 0 = {g=-a; x=-1; y=0}  then  (-1)*a + 0*0 == -a
    ()

(* Any common divisor of a and b divides every linear combination x*a + y*b. *)
assume val common_div :
  d:int -> a:int -> b:int -> x:int -> y:int ->
  Lemma
    (requires (divides d a /\ divides d b))
    (ensures  (divides d (x * a + y * b)))
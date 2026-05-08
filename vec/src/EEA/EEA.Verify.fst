module EEA.Verify

open FStar.Mul
open EEA
open EEA.Prop

(*Here we define the absolute value*)
let abs (x:int) : Tot int = if x >= 0 then x else -x

let lemma_div   = EEA.lemma_div
let lemma_bound = EEA.lemma_bound
(*transport lemmas to help the SMT move 'divides' and '>= 0'*)

assume val divides_congr_right :
  d:int -> n:int -> m:int ->
  Lemma (requires (n == m /\ divides d n))
        (ensures  (divides d m))

assume val divides_congr_left :
  g1:int -> g2:int -> n:int ->
  Lemma (requires (g1 == g2 /\ divides g1 n))
        (ensures  (divides g2 n))

assume val ge_congr_eq :
  x:int -> y:int ->
  Lemma (requires (x == y /\ x >= 0))
        (ensures  (y >= 0))

// From Bezout + the two divisibility conjuncts + nonnegativity implies is_gcd
assume val is_gcd_from_bezout :
  a:int -> b:int -> r:EEA.bezout ->
  Lemma (requires (r.g >= 0 /\ divides r.g a /\ divides r.g b 
                  /\ is_bezout_identity r a b))
        (ensures  (is_gcd r.g a b))

(*Check bezout identity holds*)
val egcd_bezout :
  a:int -> b:int ->
  Lemma (ensures (is_bezout_identity (EEA.egcd a b) a b))

let rec egcd_bezout a b
  : Lemma (ensures (is_bezout_identity (EEA.egcd a b) a b))
          (decreases (if b = 0 then 0 else abs b))
=
  if b = 0 then
    bezout_bc a
  else
    let q = a / b in
    let r = a % b in
    lemma_div a b;    // a == q*b + r
    lemma_bound a b;  // |r| < |b|

    // induction hypothesis on (b,r): is_bezout_identity (egcd b r) b r
    egcd_bezout b r;
    let rr = EEA.egcd b r in
    match EEA.egcd a b with
    | { g = g0; x = x0; y = y0 } ->
    (*From egcd(b <> 0)
     g0 = rr.g, x0 = rr.y, y0 =rr.x -q*rr.y
     Then lift coefficients from (b,r) to (a,b) gives
     rr.y * a + (rr.x - q*rr.y) * b == rr.g, which is  x0*a + y0*b == g0.
     *)
      bezout_lift a b q r rr.x rr.y rr.g

(*Now check gcd property for (egcd a b).g by induction*)

val egcd_is_gcd :
  a:int -> b:int ->
  Lemma (ensures (is_gcd (EEA.egcd a b).g a b))

let rec egcd_is_gcd a b
  : Lemma (ensures (is_gcd (EEA.egcd a b).g a b))
          (decreases (if b = 0 then 0 else abs b))
=
  if b = 0 then
    // Base: egcd a 0 = {|a|, +-1, 0}.
    let r0 = EEA.egcd a 0 in
    if a >= 0 then (
      // g = a
      assert (r0.g == a);
      assert (r0.g >= 0);
      // a == 1 * g   and   0 == 0 * g
      assert (a == 1 * r0.g);
      assert (0 == 0 * r0.g);
      ()
    ) else (
      // g = -a
      assert (r0.g == -a);
      assert (r0.g >= 0);
      // a == (-1) * g   and   0 == 0 * g
      assert (a == (-1) * r0.g);
      assert (0 == 0 * r0.g);
      ()
    );
    bezout_bc a;
    is_gcd_from_bezout a 0 r0
  else
    // Step: b <> 0
    let q = a / b in
    let r = a % b in
    lemma_div a b;    // a == q*b + r
    lemma_bound a b;  // |r| < |b|

    // introduction on (b,r): rr.g is gcd(b,r)
    egcd_is_gcd b r;
    let rr  = EEA.egcd b r in

    // From introduction hypoth: rr.g divides b and r, therefore divides (q*b + r)
    common_div rr.g b r q 1;
    assert (a == q * b + r);
    // Move divisibility across equality to get rr.g | a
    divides_congr_right rr.g (q*b + r) a;

    // Current result and its fields
    let cur = EEA.egcd a b in
    match cur with
    | { g = g0; x = x0; y = y0 } ->
      // egcd preserves the gcd component in the b <> 0
      assert (g0 == rr.g);
      // Transport nonnegativity and divisibility facts to g0
      ge_congr_eq rr.g g0;
      divides_congr_left rr.g g0 b;  // rr.g | b  then  g0 | b
      divides_congr_left rr.g g0 a;  // rr.g | a  then  g0 | a

      // give Bezout for (a,b); with the two divides and g0 >= 0,
      egcd_bezout a b;
      is_gcd_from_bezout a b cur

//check both true
val egcd_true :
  a:int -> b:int ->
  Lemma (ensures (let r = EEA.egcd a b in eea_correctness_conditions r a b))
let egcd_true a b =
  egcd_bezout a b;
  egcd_is_gcd a b
module EEA
open FStar.Mul (*For using multiplication * *)

(*Firstly define a type for Bezout's identity *)
type bezout ={
  g:int;  (*gcd value*)
  x:int; 
  y:int;
}

assume val lemma_div 
  :a:int -> b:int{ b <> 0} ->
  Lemma (ensures a == (a / b) * b + (a % b))

assume val lemma_bound 
  :a:int -> b:int{ b <> 0} ->
  Lemma (ensures abs (a % b) < abs b)

let rec egcd (a:int) (b:int) (*starts a recursive function egcd*)
  : Tot bezout 
  (*For now, tell Fstar that this might diverge, 
    this should be changed to Tot and add decreases when verifying*)
  (decreases (if b=0 then 0 else (if b>=0 then b else -b)))
=
  if b=0 then (*base case*)
  (*if a>=0, gcd is a, (x,y)=(1,0), 1*a + 0*b = a 
    if a<0, gcd is -a to make it nonnegative, (x,y) = (-1,0) -1*a + 0*b = -a*)
    if a>= 0 then {   
      g = a;
      x = 1;
      y = 0
    }
    else{
      g = -a;
      x = -1;
      y = 0
    }
  else
    let q = a / b in  //quotient of a by b
    let r = a % b in //r is the remainder, such that a=q*b+r
    lemma_bound a b;
    let ri = egcd b r in  //recursive step, where ri is bezout type
    {g = ri.g; x=ri.y; y=ri.x - q*ri.y} // Here it returns to bezout type
extern crate bellman_ce;
extern crate rand;
extern crate phase2;
extern crate memmap;
extern crate num_bigint;
extern crate num_traits;
extern crate exitcode;

#[macro_use]
extern crate serde;
extern crate serde_json;

// For randomness (during paramgen and proof generation)
use rand::ChaChaRng;

use std::str;
use std::fs::File;

// Bring in some tools for using pairing-friendly curves
use bellman_ce::pairing::{
    Engine,
    ff::PrimeField,
};

// We'll use these interfaces to construct our circuit.
use bellman_ce::{
    Circuit,
    Variable,
    Index,
    LinearCombination,
    ConstraintSystem,
    SynthesisError
};

use std::collections::BTreeMap;

#[derive(Serialize, Deserialize)]
struct CircuitJson {
    pub constraints: Vec<Vec<BTreeMap<String, String>>>,
    #[serde(rename = "nPubInputs")]
    pub num_inputs: usize,
    #[serde(rename = "nOutputs")]
    pub num_outputs: usize,
    #[serde(rename = "nVars")]
    pub num_variables: usize,
}

struct CircomCircuit<'a> {
    pub file_name: &'a str,
}

/// Our demo circuit implements this `Circuit` trait which
/// is used during paramgen and proving in order to
/// synthesize the constraint system.
impl<'a, E: Engine> Circuit<E> for CircomCircuit<'a> {
    fn synthesize<CS: ConstraintSystem<E>>(
        self,
        cs: &mut CS
    ) -> Result<(), SynthesisError>
    {
        let mmap = unsafe { memmap::Mmap::map(&File::open(self.file_name)?) }?;
        let content = str::from_utf8(&mmap).unwrap();
        let circuit_json: CircuitJson = serde_json::from_str(&content).unwrap();
        let num_public_inputs = circuit_json.num_inputs + circuit_json.num_outputs + 1;
        //println!("num public inputs: {}", num_public_inputs);
        for i in 1..circuit_json.num_variables {
            if i < num_public_inputs {
                //println!("allocating public input {}", i);
                cs.alloc_input(|| format!("variable {}", i), || {
                    //println!("variable {}: {}", i, &self.witness[i]);
                    Ok(E::Fr::from_str("1").unwrap())
                });
            } else {
                //println!("allocating private input {}", i);
                cs.alloc(|| format!("variable {}", i), || {
                    //println!("variable {}: {}", i, &self.witness[i]);
                    Ok(E::Fr::from_str("1").unwrap())
                });
            }
        }
        let mut constrained: BTreeMap<usize, bool> = BTreeMap::new();
        let mut constraint_num = 0;
        for (i, constraint) in circuit_json.constraints.iter().enumerate() {
            let mut lcs = vec![];
            for lc_description in constraint {
                let mut lc = LinearCombination::<E>::zero();
                //println!("lc_description: {:?}, i: {}, len: {}", lc_description, i, constraint.len());
                for (var_index_str, coefficient_str) in lc_description {
                    //println!("var_index_str: {}, coefficient_str: {}", var_index_str, coefficient_str);
                    let var_index_num: usize = var_index_str.parse().unwrap();
                    let var_index = if var_index_num < num_public_inputs {
                        Index::Input(var_index_num)
                    } else {
                        Index::Aux(var_index_num - num_public_inputs)
                    };
                    constrained.insert(var_index_num, true);
                    if i == 2 {
                        lc = lc + (E::Fr::from_str(coefficient_str).unwrap(), Variable::new_unchecked(var_index));
                    } else {
                        lc = lc + (E::Fr::from_str(coefficient_str).unwrap(), Variable::new_unchecked(var_index));
                    }
                }
                lcs.push(lc);
            }
            cs.enforce(|| format!("constraint {}", constraint_num), |_| lcs[0].clone(), |_| lcs[1].clone(), |_| lcs[2].clone());
            constraint_num += 1;
        }
        println!("constraints: {}", circuit_json.constraints.len());
        let mut unconstrained: BTreeMap<usize, bool> = BTreeMap::new();
        for i in 0..circuit_json.num_variables {
            if !constrained.contains_key(&i) {
                unconstrained.insert(i, true);
            }
        }
        for (i, _) in unconstrained {
            println!("variable {} is unconstrained", i);
        }
        Ok(())
    }
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.len() != 3 {
        println!("Usage: \n<in_circuit.json> <out_params.params>");
        std::process::exit(exitcode::USAGE);
    }
    let circuit_filename = &args[1];
    let params_filename = &args[2];

    let mut rng = ChaChaRng::new_unseeded();
    rng.set_counter(0u64, 1234567890u64);
    let rng = &mut rng;

    // Import the circuit and create the initial parameters using phase 1
    println!("Creating initial parameters for {}...", circuit_filename);
    let should_filter_points_at_infinity = false;
    let params = {
        let c = CircomCircuit {
            file_name: &circuit_filename,
        };
        phase2::MPCParameters::new(c, should_filter_points_at_infinity).unwrap()
    };

    println!("Writing initial parameters to {}.", params_filename);
    let mut f = File::create(params_filename).unwrap();
    params.write(&mut f).expect("unable to write params");
}

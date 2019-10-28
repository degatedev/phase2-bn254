extern crate bellman_ce;
extern crate rand;
extern crate phase2;
extern crate memmap;
extern crate num_bigint;
extern crate num_traits;
extern crate blake2;
extern crate byteorder;
extern crate exitcode;

// For randomness (during paramgen and proof generation)
use rand::Rng;

// For benchmarking
use std::time::{Duration, Instant};
use std::str;

use std::fs::File;
use std::fs::OpenOptions;
use std::io::Write;

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

#[macro_use]
extern crate serde;
extern crate serde_json;

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
    if args.len() != 4 {
        println!("Usage: \n<in_circuit.json> <in_old_params.params> <in_new_params.params>");
        std::process::exit(exitcode::USAGE);
    }
    let circuit_filename = &args[1];
    let old_params_filename = &args[2];
    let new_params_filename = &args[3];

    let old_reader = OpenOptions::new()
                                .read(true)
                                .open(old_params_filename)
                                .expect("unable to open old params");
    let mut old_params = phase2::MPCParameters::read(old_reader, true).expect("unable to read old params");

    let new_reader = OpenOptions::new()
                                .read(true)
                                .open(new_params_filename)
                                .expect("unable to open new params");
    let mut new_params = phase2::MPCParameters::read(new_reader, true).expect("unable to read new params");

    println!("Checking contribution {}...", new_params_filename);
    let contribution = phase2::verify_contribution(&old_params, &new_params).expect("should verify");

    let should_filter_points_at_infinity = false;
    let verification_result = new_params.verify(CircomCircuit {
        file_name: &circuit_filename,
    }, should_filter_points_at_infinity).unwrap();
    assert!(phase2::contains_contribution(&verification_result, &contribution));
    println!("Contribution {} verified.", new_params_filename);
}

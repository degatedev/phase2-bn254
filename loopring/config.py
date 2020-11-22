import os.path
import hashlib
import json
import subprocess

# Set this to the folder containing the phase2 repo
phase2_repo_path = "../../phase2-bn254/"

# Set this to the folder containing the phase2 repo
protocol3_repo_path = "../../protocols/packages/loopring_v3/"

# Do the mpc for the following circuits
circuits = [ \
    [0, False, [16, 64, 128, 192, 256, 320, 384, 448, 512]], \
]

# Set this to the folder containing the phase2 repo
circuit_executable = protocol3_repo_path + "build/circuit/dex_circuit"

class Circuit(object):
    def __init__(self, blockType, blockSize, onchainDataAvailability):
        self.blockType = blockType
        self.blockSize = blockSize
        self.onchainDataAvailability = onchainDataAvailability

def str_da(onchainDataAvailability):
    return "_"

def base_name(circuit):
    str_block_types = ["all"]
    return str_block_types[circuit.blockType] + str_da(circuit.onchainDataAvailability) + str(circuit.blockSize)

def get_block_filename(circuit):
    return "blocks/block_meta_" + base_name(circuit) + ".json"

def get_circuit_filename(circuit):
    return "circuits/circuit_" + base_name(circuit) + ".json"

def get_params_filename(circuit):
    return "params/params_" + base_name(circuit) + ".params"

def get_old_params_filename(circuit):
    return "old_params/params_" + base_name(circuit) + ".params"

def get_bellman_vk_filename(circuit):
    return "keys/" + base_name(circuit) + "_vk.json"

def get_bellman_pk_filename(circuit):
    return "keys/" + base_name(circuit) + "_pk.json"

def get_vk_filename(circuit):
    return protocol3_repo_path + "keys/" + base_name(circuit) + "_vk.json"

def get_pk_filename(circuit):
    return protocol3_repo_path + "keys/" + base_name(circuit) + "_pk.raw"

def get_zip_filename(index):
    str_index = str(index)
    while len(str_index) < 4:
        str_index = "0" + str_index
    return "loopring_mpc_" + str_index + ".zip"

def find_latest_contribution_index():
    index = 1000
    while index >= 0:
        if os.path.isfile(get_zip_filename(index)):
            return index
        index -= 1
    raise ValueError('Could not find any contribution!')

def hash_file(filename):
    hash = hashlib.sha256()
    with open(filename, "rb") as f:
        for block in iter(lambda: f.read(4096), b""):
            hash.update(block)
        return "0x" + hash.hexdigest()

def get_circuits():
    circuit_list = []
    for block_permutations in circuits:
        blockType = block_permutations[0]
        onchainDataAvailability = block_permutations[1]
        for blockSize in block_permutations[2]:
            circuit_list.append(Circuit(blockType, blockSize, onchainDataAvailability))
    return circuit_list

class Struct(object): pass
def generate_block(circuit):
    block = Struct()
    block.onchainDataAvailability = circuit.onchainDataAvailability
    block.blockType = circuit.blockType
    block.blockSize = circuit.blockSize
    blockJson = json.dumps(block, default=lambda o: o.__dict__, sort_keys=True, indent=4)

    block = get_block_filename(circuit)
    if not os.path.exists(block):
        os.makedirs(os.path.dirname(block), exist_ok=True)
    f = open(block, "w+")
    f.write(blockJson)
    f.close()
    return block

def export_circuit(circuit):
    block = get_block_filename(circuit)
    circuit_filename = get_circuit_filename(circuit)
    if not os.path.exists(circuit_filename):
        os.makedirs(os.path.dirname(circuit_filename), exist_ok=True)
    subprocess.check_call([circuit_executable, "-exportcircuit", block, circuit_filename])
    return circuit_filename


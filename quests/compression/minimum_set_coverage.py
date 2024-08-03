import numpy as np 
from quests.entropy import delta_entropy

DEFAULT_CUTOFF: float = 5.0
DEFAULT_K: int = 32
EPS: float = 1e-15
DEFAULT_H: float = 0.015
DEFAULT_BS: int = 10000

def find_key(input_dict: dict, target: np.ndarray):
    
    """Given a dictionary of descriptors, determines the index of the target descriptors
    
    Arguments: 
        input_dict (dictionary): dictionary containing descriptors
        target (np.ndarray): numpy array of descriptor
        
    Returns: key (int): original index 
        
        
    """
    
    for key in input_dict:
        if (target.shape != input_dict[key].shape):
            continue
        if (target == input_dict[key]).all():
            return key
    return None
        
def minimum_set_coverage(frames: list, initial_entropies: np.ndarray, descriptor_dict: dict, h: float, l: float):
    
    """Given the frames and initial entropies, determine the most diverse set of atoms in the set
    
    Arguments: 
        frames (list): descriptors of each of the frames
        initial_entropies (np.ndarray): array with initial entropies of each of the frames
        descriptor_dict (dict): dictionary containing descriptors
        h (float): h value
        l (float): lambda value 
        
    Returns: indexes (list): list of indexes of the most diverse frames in order 
        
        
    """
    
    indexes = []
    
    compressed_data = frames[initial_entropies.argmax()]
    indexes.append(initial_entropies.argmax())
    frames.pop(initial_entropies.argmax())
    
    # loop to find order of values 
    
    for i in range(len(frames)):
        entropy = np.zeros(len(frames))
        for a in range(len(frames)):
            entropy[a] = np.mean(delta_entropy(frames[a], compressed_data, h = h)) + l*initial_entropies[find_key(descriptor_dict, frames[a])]
        compressed_data = np.concatenate((compressed_data, frames[entropy.argmax()]), axis = 0)
        indexes.append(find_key(descriptor_dict, frames[entropy.argmax()]))
        frames.pop(entropy.argmax())
    
    return indexes
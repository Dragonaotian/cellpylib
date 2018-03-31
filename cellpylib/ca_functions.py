import random

import matplotlib.pyplot as plt
import numpy as np


def plot(ca, title=''):
    cmap = plt.get_cmap('Greys')
    plt.title(title)
    plt.imshow(ca, interpolation='none', cmap=cmap)
    plt.show()


def evolve(cellular_automaton, n_steps, apply_rule, r=1):
    _, cols = cellular_automaton.shape
    array = np.zeros((n_steps, cols), dtype=np.int)
    array[0] = cellular_automaton

    def index_strides(arr, window_size):
        # this function is based on code in http://www.credid.io/cellular-automata-python-2.html
        arr = np.concatenate((arr[-window_size//2+1:], arr, arr[:window_size//2]))
        shape = arr.shape[:-1] + (arr.shape[-1] - window_size + 1, window_size)
        strides = arr.strides + (arr.strides[-1],)
        return np.lib.stride_tricks.as_strided(arr, shape=shape, strides=strides)

    for i in range(1, n_steps):
        cells = array[i - 1]
        strides = index_strides(np.arange(len(cells)), 2*r + 1)
        states = cells[strides]
        array[i] = np.array([apply_rule(s, c) for c, s in enumerate(states)])
    return array


def bits_to_int(bits):
    total = 0
    for shift, j in enumerate(bits[::-1]):
        if j:
            total += 1 << shift
    return total


def int_to_bits(num, num_digits):
    converted = list(map(int, bin(num)[2:]))
    return np.pad(converted, (num_digits - len(converted), 0), 'constant')


def nks_rule(state, rule):
    """
    convert state to int, so [1,0,1] -> 5, call this state_int
    convert rule to binary, so 254 -> [1,1,1,1,1,1,1,0], call this rule_bin_array
    new value is rule_bin_array[7 - state_int]
      we subtract 7 from state_int to be consistent with the numbering scheme used in NKS
      in NKS, rule 254 for a 1D binary cellular automaton is described as:
        [1,1,1]  [1,1,0]  [1,0,1]  [1,0,0]  [0,1,1]  [0,1,0]  [0,0,1]  [0,0,0]
           1        1        1        1        1        1        1        0
    :param state: a binary array of length 3
    :param rule: an int, from 0 to 255, indicating the cellular automaton rule number in NKS convention
    :return: the result, 0 or 1, of applying the given NKS rule on the given state 
    """
    state_int = bits_to_int(state)
    n = 2**len(state)
    rule_bin_array = int_to_bits(rule, n)
    return rule_bin_array[(n-1) - state_int]


def number_rule(state, rule):
    """
    The same idea as the NKS rule, except that the neighbourhoods are listed in 
      lexicographic order (the reverse of the NKS convention).
    :param state: a binary array of length 2r + 1
    :param rule: an int indicating the cellular automaton rule number
    :return: the result, 0 or 1, of applying the given rule on the given state
    """
    state_int = bits_to_int(state)
    rule_bin_array = int_to_bits(rule, 2**len(state))
    return rule_bin_array[state_int]


def totalistic_rule(state, k, rule):
    """
    The totalistic rule as described in NKS. The average color is mapped to a whole number in [0, k - 1].
    The rule number is in base 10, but interpreted in base k. For a 1-dimensional cellular automaton, there are
    3k - 2 possible average colors in the cell neighbourhood.
    :param state: a k-color array of length 2r + 1
    :param k: the number of colors in this cellular automaton, where only 2 <= k <= 36 is supported
    :param rule: the k-color cellular automaton rule number in base 10, interpreted in base k
    :return: the result, a number from 0 to k - 1, of applying the given rule on the given state
    """
    # e.g. np.base_repr(777, base=3) -> '1001210'; the zfill pads the string with zeroes: '1'.zfill(3) -> '001'
    #   Bases greater than 36 not handled in base_repr.
    rule_string = np.base_repr(rule, base=k).zfill(3*k - 2)
    if len(rule_string) > 3*k - 2:
        raise Exception("rule number out of range")
    state_sum = sum(state)
    # the rightmost element of the rule is for the average color 0, in NKS convention
    return int(rule_string[(3*k - 3) - state_sum], k)


def table_rule(state, table):
    """
    A rule where the state is converted into a string, and looked up in the given table, to yield the return value.
    :param state: a k-color array of length 2r + 1
    :param table: a table (map) of string representations of each neighbourhood state to the associated next 
           cell state value; for example, for k = 2 and r = 2, a valid table might be: 
           {'101': 1, '111': 0, '011': 0, '110': 1, '000': 0, '100': 0, '010': 0, '001': 1}
    :return: a number, from 0 to k - 1, associated with the given state as specified in the given table
    """
    state_repr = ''.join(str(x) for x in state)
    if not state_repr in table:
        raise Exception("could not find state '%s' in table" % state_repr)
    return table[state_repr]


def random_rule_table(k, r, lambda_val=None, quiescent_state=None, strong_quiescence=False, isotropic=False):
    """
    Constructs and returns a random rule table, as described in [Langton, C. G. (1990). Computation at the edge of 
    chaos: phase transitions and emergent computation. Physica D: Nonlinear Phenomena, 42(1-3), 12-37.], using 
    the "random-table" method.
    :param k: the number of cell states
    :param r: the radius of the cellular automaton neighbourhood
    :param lambda_val: a real number in (0., 1.), representing the value of lambda; if None, a default value of 
                       1.0 - 1/k will be used, where all states will be represented equally in the rule table
    :param quiescent_state: the state, a number in {0,...,k - 1}, to use as the quiescent state
    :param strong_quiescence: if True, all neighbourhood states uniform in cell state i will map to cell state i
    :param isotropic: if True, all planar rotations of a neighbourhood state will map to the same cell state
    :return: a tuple containing: a table describing a rule, constructed using the "random-table" table method as 
             described by C. G. Langton, the actual lambda value, and the quiescent state used
    """
    states = []
    n = 2*r + 1
    for i in range(0, k**n):
        states.append(np.base_repr(i, k).zfill(n))
    table = {}
    if lambda_val is None:
        lambda_val = 1. - (1. / k)
    if quiescent_state is None:
        quiescent_state = np.random.randint(k, dtype=np.int)
    if not (0 <= quiescent_state <= k - 1):
        raise Exception("quiescent state must be a number in {0,...,k - 1}")
    other_states = [x for x in range(0, k) if x != quiescent_state]
    quiescent_state_count = 0
    for state in states:
        if strong_quiescence and len(set(state)) == 1:
            # if the cell states in neighbourhood are all the same, e.g. '111'
            next_state = int(state[0], k)
            if next_state == quiescent_state: quiescent_state_count += 1
        else:
            state_reversed = state[::-1]
            if isotropic and state_reversed in table:
                next_state = table[state_reversed]
                if next_state == quiescent_state: quiescent_state_count += 1
            else:
                if random.random() < (1. - lambda_val):
                    next_state = quiescent_state
                    quiescent_state_count += 1
                else:
                    next_state = random.choice(other_states)
        table[state] = next_state
    actual_lambda_val = (k**n - quiescent_state_count) / k**n
    return table, actual_lambda_val, quiescent_state


def init_simple(size, val=1):
    """
    Returns an array initialized with zeroes, with its center value set to the specified value, or 1 by default.
    :param size: the size of the array to be created 
    :param val: the value to be used in the center of the array (1, by default)
    :return: an array with specified size, with its center value initialized to the specified value, or 1 by default 
    """
    x = np.zeros(size, dtype=np.int)
    x[len(x)//2] = val
    return np.array([x])


def init_random(size, k=2):
    """
    Returns a randomly initialized array with values consisting of numbers in {0,...,k - 1}, where k = 2 by default.
    :param size: the size of the array to be created
    :param k: the number of states in the cellular automaton (2, by default)
    :return: an array with the specified size, randomly initialized with numbers in {0,...,k - 1}
    """
    return np.array([np.random.randint(k, size=size, dtype=np.int)])

# -*- coding: utf-8 -*-
"""
@author: chich
"""


import lithops 
import time
import numpy as np
import pickle
from phe import paillier

# =============================================================================
# Reducer verision of the ipmlementtion
# =============================================================================
# =============================================================================
# Map function that calculates the blocks of the output matrix
# =============================================================================
def mapfunc(id,namespace,indi,storage):

    # Call from the server our matrices
    A = storage.get_object(namespace, 'Amat')
    A = pickle.loads(A)
    B = storage.get_object(namespace, 'Bmat')
    B = pickle.loads(B)

    row_block = A[indi[0]*a:(indi[0]+1)*a, :]
    col_block = B[:, indi[1]*a:(indi[1]+1)*a]
    C[indi[0]*a:(indi[0]+1)*a, indi[1]*a:(indi[1]+1)*a] = np.dot(row_block, col_block)
    # Store them with id when block is computed
    storage.put_object(namespace, 'Cmat {}'.format(id)  , pickle.dumps(C))
    
# =============================================================================
# Reduce function that takes all blocks and sums them to reduce on the remote 
# server.    
# =============================================================================
def reduce_func(namespace, n_workers, storage):    
    res = []
    for i in range(n_workers):
        #We append the results in a list 
        res.append(pickle.loads(storage.get_object(namespace, 'Cmat {}'.format(i))))
    # We sum all the blocks
    sol = sum(res)

    return sol


if __name__ == "__main__":
    # Set up matrix sizes
    m = 3000
    n = 1500
    l = 3000
    # We create two matrixes randomly
    A = np.random.randint(10, size=(m, n))
    B = np.random.randint(10, size=(n, l))
    # Create empty C matrix of zeros of size m*l
    C = np.zeros((m, l))
    #  Size of blocks
    a = 1500
    # We do some checks in order to verify the sizes
    if not A.shape[1] == B.shape[0]:
        raise ValueError(f'''The number of columns in matrix A
                    must be equal to the number of rows in matrix B.''')
    if m % a != 0:
        raise ValueError(f'The number of rows in A is not divisible by {a}')

    if l % a != 0:
        raise ValueError(f'The number of columns in B is not divisible by {a}')



# =============================================================================
# Pickle storage
# =============================================================================
    namespace = 'mat_mult'
    storage = lithops.Storage() 
    storage.put_object(namespace, 'Amat', pickle.dumps(A))
    storage.put_object(namespace, 'Bmat', pickle.dumps(B))
    
    # We create a list of two dimensional indices and give it also namespace
    indi = []
    for i in range(m//a):
        for j in range(l//a):          
            indi.append((namespace,(i,j)))
            
    # We will create len(indi) workers
    n_workers = len(indi)
# =============================================================================
# Plain text multiplication
# =============================================================================
    # Start the timer to analyze function speed
    start_time = time.time()

    # Initiate lithops executor
    fexec = lithops.FunctionExecutor()
    # Call map function and give as argument function name and list of indices
    # with namespace
    fexec.map(mapfunc, indi)
    # Blocking the call to get the results
    fexec.wait()
    # Call reduce function with namespace and number of workers
    fexec.call_async(reduce_func, [namespace, n_workers])
    # Call for the results
    cPlain = fexec.get_result()
    print("--- %s seconds for plain---" % (time.time() - start_time))
# =============================================================================
# Use  numpy function
# =============================================================================
    start_time = time.time()
    cNumpy = np.matmul(A, B)  
    print("--- %s seconds  for numpy function---" % (time.time() - start_time))
# =============================================================================
#  Crypted multiplication    
# =============================================================================
    # Start the timer to analyze function speed
    start_time = time.time()
    # Genrate private and public key for encryption and decryption
    public_key, private_key = paillier.generate_paillier_keypair()
    # Encrypt matrix B, store as np matrix, reshape it
    B = np.array([public_key.encrypt(int(z)) for x in B for z in x]).reshape(n,l)
    # Update the server matrix B
    storage.put_object(namespace, 'Bmat', pickle.dumps(B))
    # Create empty C matrix of zeros of size m*l
    # Specify array of object to gove it crypted objects later
    C = np.zeros((m, l),dtype = object)
    # Initiat lithops executor
    fexec = lithops.FunctionExecutor()
    # Call map function and give as argument function name and list of indices
    fexec.map(mapfunc, indi)
    # Blocking the call to get the results
    fexec.wait()
    # Call reduce function
    fexec.call_async(reduce_func, [namespace, n_workers])
    cCrypt = fexec.get_result()

    print("--- %s seconds for crypted without decrypt---" % (time.time() - start_time))
    # We decrypt the result matrix with private key
    cDecrypt = np.array([private_key.decrypt(z) for x in cCrypt for z in x]).reshape(m,l)
    print("--- %s seconds for crypted with decyrpt---" % (time.time() - start_time))
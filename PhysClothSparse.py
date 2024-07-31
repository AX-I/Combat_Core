
import numpy as np
from scipy.linalg import cho_factor, cho_solve

import scipy.sparse as sparse
import scipy.sparse.linalg as splinalg

def signed_incidence_matrix_sparse(n, E):
  ijv = []
  for i in range(E.shape[0]):
    ijv.append((i,E[i,0],-1))
    ijv.append((i,E[i,1],1))
  ijv = np.array(ijv).T
  A = sparse.coo_matrix((ijv[2], (ijv[0], ijv[1])), shape=(E.shape[0], n))
  return A

def constructPinnedSparse(b, n):
  ijc = []
  for i in range(b.shape[0]):
    ijc.append((i,b[i],1))
  ijc = np.array(ijc).T
  C = sparse.coo_matrix((ijc[2], (ijc[0], ijc[1])), shape=(b.shape[0], n))
  return C

class MassSprings:
  def __init__(self, V: np.array, E: np.array, k: float,
               m: np.array, b: np.array, dt: float):
    """V: (n,3), E: (e,2), k: spring const, m: (n,), b: pinned indices"""

    self.V = V * 1.0
    self.E = E
    self.k = k
    self.b = b
    self.dt = dt

    self.Uprev = V * 1.0
    self.Ucur = V * 1.0

    r = np.zeros((E.shape[0],))
    for i in range(E.shape[0]):
      r[i] = np.linalg.norm(V[E[i,0]] - V[E[i,1]])
    self.r = r

    n = V.shape[0]

    M = sparse.coo_matrix((m, (np.arange(n), np.arange(n))), shape=(n,n)).tocsr()
    self.M = M

    A = signed_incidence_matrix_sparse(n, E)
    self.A = A
    self.AT = A.transpose().tocsr()

    Q = k * A.transpose() @ A + 1 / (dt * dt) * M

    self.C = constructPinnedSparse(b, n)

    Q += 10**10 * self.C.transpose() @ self.C
    self.Q = Q

    self.prefactorization = splinalg.splu(Q)

    self.pinnedConst = 10**10 * self.C.transpose() @ self.C @ self.V

    self.Ei0 = E[:,0].flatten()
    self.Ei1 = E[:,1].flatten()

  def step(self, fext):
    d = np.zeros((self.E.shape[0], 3))
    E = self.E

    Unext = self.Ucur * 1.0

    for x in range(16):
      d = Unext[self.Ei1] - Unext[self.Ei0]
      d *= (1 / np.linalg.norm(d, axis=1) * self.r)[:,None]

      y = 1 / (self.dt*self.dt) * self.M.dot(2*self.Ucur - self.Uprev) + fext

      bSolve = self.k * self.AT @ d + y

      bSolve += self.pinnedConst

      Unext = self.prefactorization.solve(bSolve)

    self.Uprev = self.Ucur * 1.0
    self.Ucur = Unext * 1.0


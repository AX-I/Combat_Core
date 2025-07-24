
import numpy as np

from scipy.linalg import cho_factor, cho_solve

import scipy.sparse as sparse
import scipy.sparse.linalg as splinalg

F32 = np.float32

def signed_incidence_matrix(n, E):
  A = np.zeros((E.shape[0], n), dtype=F32)
  for i in range(E.shape[0]):
    A[i,E[i,0]] = -1
    A[i,E[i,1]] = 1
  return A

def signed_incidence_matrix_sparse(n, E):
  ijv = []
  for i in range(E.shape[0]):
    ijv.append((i,E[i,0],-1))
    ijv.append((i,E[i,1],1))
  ijv = np.array(ijv).T
  A = sparse.coo_matrix((ijv[2], (ijv[0], ijv[1])), shape=(E.shape[0], n), dtype=F32)
  return A

def constructPinned(b, n):
  C = np.zeros((b.shape[0], n), dtype=F32)
  for i in range(b.shape[0]):
      C[i,b[i]] = 1
  return C

def constructPinnedSparse(b, n):
  ijc = []
  for i in range(b.shape[0]):
    ijc.append((i,b[i],1))
  ijc = np.array(ijc).T
  C = sparse.coo_matrix((ijc[2], (ijc[0], ijc[1])), shape=(b.shape[0], n), dtype=F32)
  return C

class MassSprings:
  def __init__(self, V: np.array, E: np.array, k: float,
               m: np.array, b: np.array, dt: float,
               damp=0.0, useSparse=True):
    """V: (n,3), E: (e,2), k: spring const, m: (n,), b: pinned indices"""

    self.V = V.astype(F32)
    self.E = E.astype(F32)
    self.k = F32(k)
    self.b = F32(b)
    self.dt = F32(dt)

    self.damp = F32(1 - damp)

    self.Uprev = self.V * F32(1.0)
    self.Ucur = self.V * F32(1.0)

    self.r = np.linalg.norm(V[E[:,0]] - V[E[:,1]], axis=1)

    n = V.shape[0]

    if useSparse:
      M = sparse.coo_matrix((m, (np.arange(n), np.arange(n))), shape=(n,n), dtype=F32).tocsr()

      A = signed_incidence_matrix_sparse(n, E)
      self.kAT = self.k * A.transpose().tocsr()

      self.C = constructPinnedSparse(b, n)

    else:
      M = (np.identity(n) * m).astype(F32)

      A = signed_incidence_matrix(n, E)
      self.kAT = self.k * A.transpose()

      self.C = constructPinned(b, n)

    self.M = M

    Q = k * A.transpose() @ A + 1 / (dt * dt) * M

    Q += F32(10**10) * self.C.transpose() @ self.C
    self.Q = Q

    if useSparse:
      self.prefactorization = splinalg.splu(Q)
      self.preSolve = self.prefactorization.solve
    else:
      self.prefactorization = cho_factor(Q)
      self.preSolve = lambda x: cho_solve(self.prefactorization, x)

    self.pinnedConst = F32(10**10) * self.C.transpose() @ self.C @ self.V

    self.Ei0 = E[:,0].flatten()
    self.Ei1 = E[:,1].flatten()

  def step(self, fext, collider=None, collVMult=1, iters=16):
    Unext = self.Ucur * F32(1.0)

    y = 1 / (self.dt*self.dt) * self.M.dot(self.Ucur + self.damp*(self.Ucur - self.Uprev)) + fext

    for x in range(iters):
      d = Unext[self.Ei1] - Unext[self.Ei0]
      d *= (self.r / np.linalg.norm(d, axis=1))[:,None]

      bSolve = self.kAT @ d + y
      bSolve += self.pinnedConst

      Unext = self.preSolve(bSolve)

    if collider:
      assert collider.t == 'Circle'
      EPSILON = 0.01
      buffer = 0.5
      R = Unext - collider.pos[None,:]
      d = np.sqrt(np.einsum('ij, ij->i', R, R))
      cond = d < collider.dim
      if np.any(cond):
        Unext[cond] += (collider.dim-d[cond]+EPSILON)[:,None] * R[cond] \
                       + collider.rb.v[None,:] * collVMult*self.dt * (collider.dim-d[cond])[:,None]/collider.dim

    self.Uprev = self.Ucur
    self.Ucur = Unext * F32(1.0)


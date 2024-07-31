
import numpy as np
from scipy.linalg import cho_factor, cho_solve

def signed_incidence_matrix(n, E):
  A = np.zeros((E.shape[0], n))
  for i in range(E.shape[0]):
    A[i,E[i,0]] = -1
    A[i,E[i,1]] = 1
  return A

class MassSprings:
  def __init__(self, V, E, k, m, b, dt):
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

    M = np.identity(n)
    for i in range(n):
      M[i,i] = m[i]
    self.M = M

    A = signed_incidence_matrix(n, E)
    self.A = A

    Q = k * A.transpose() @ A + 1 / (dt * dt) * M

    C = np.zeros((b.shape[0], n))
    for i in range(b.shape[0]):
        C[i,b[i]] = 1
    self.C = C

    Q += 10**10 * C.transpose() @ C

    self.Q = Q

    self.prefactorization = cho_factor(Q)

    self.pinnedConst = 10**10 * C.transpose() @ C @ self.V

    self.Ei0 = E[:,0].flatten()
    self.Ei1 = E[:,1].flatten()

  def step(self, fext):
    d = np.zeros((self.E.shape[0], 3))
    E = self.E

    Unext = self.Ucur * 1.0

    for x in range(16):
      d = Unext[self.Ei1] - Unext[self.Ei0]
      d *= (1 / np.linalg.norm(d, axis=1) * self.r)[:,None]

      y = 1 / (self.dt*self.dt) * self.M \
          @ (2*self.Ucur - self.Uprev) + fext

      bSolve = self.k * self.A.transpose() @ d + y

      bSolve += self.pinnedConst

      Unext = cho_solve(self.prefactorization, bSolve)

    self.Uprev = self.Ucur * 1.0
    self.Ucur = Unext * 1.0


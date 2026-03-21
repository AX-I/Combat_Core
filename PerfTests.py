
from VertObjects import VertModel
from profilehooks import profile
import time

class MockViewer:
    def __init__(self):
        self.vtNames = {}; self.vaNames = {}
        self.vtextures = []; self.texAlphas = []
        self.vertpoints = []; self.vertnorms = []
        self.vertu = []; self.vertv = []
        self.vertBones = []; self.matShaders = {}
        self.vertObjects = []
    def loadTexture(self, *args):
        return args

#@profile(stdout=open('profile/vcreate.txt', 'w'), filename='profile/vcreate.pstats')
def testObjLoad(testFile, **ex):
    global v, m
    v = MockViewer()

    st = time.time()
    m = VertModel(v, [0,0,0], filename=testFile, cache=False, **ex)
    v.vertObjects.append(m)
    print(f'init   {time.time() - st:.2f}s')
    for o in v.vertObjects:
        o.create()
    print(f'create {time.time() - st:.2f}s')

    totWedges = sum(len(vo.wedgePoints) for vo in v.vertObjects)
    print(totWedges, 'tris')
    print([len(vo.wedgePoints) for vo in v.vertObjects])

testObjLoad('../Models/Body/B10Fc.obj', animated=True)

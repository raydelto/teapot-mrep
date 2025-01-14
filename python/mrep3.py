from math import comb
from guptri_py import *

import numpy as np
from scipy.linalg import null_space, eigvals
import matplotlib.pyplot as plt

def bernstein(i, degree, u):
    ''' Returns a Berstein polynomial

        i = polynomial number
        degree = degree
        u = sample points
    '''
    return comb(degree, i) * np.power(u, i) * np.power(1 - u, degree - i)

def bernstein_deriv(i, degree, u):
    ''' Returns the first derivative Berstein polynomial

        i = polynomial number
        degree = degree
        u = sample points
    '''

    if i:
        a = i * np.power(u, i - 1) * np.power(1 - u, degree - i)
    else:
        a = 0
    if degree - i:
        b = -np.power(u, i) * (degree - i) * np.power(1 - u, degree - i - 1)
    else:
        b = 0
    return comb(degree, i) * (a + b)

def sample_surface(b, n=10, u=None, v=None):
    ''' Samples a Bezier surface

        b = sample points (shape is [degree + 1, degree + 1, dimension])
        n = number of points to generate on each axis (in the range 0,1)
    '''
    degree1 = b.shape[0] - 1
    degree2 = b.shape[1] - 1
    dimension = b.shape[2]
    if u is None:
        u = np.linspace(0, 1, n)
    elif isinstance(u, float):
        u = np.array([u])
    if v is None:
        v = np.linspace(0, 1, n)
    elif isinstance(v, float):
        v = np.array([v])
    out = np.zeros([len(u), len(v), dimension])
    for i in range(degree1 + 1):
        for j in range(degree2 + 1):
            wu = bernstein(i, degree1, u)
            wv = bernstein(j, degree2, v)
            w = wu.reshape(-1,1).dot(wv.reshape(1,-1))
            s = np.dstack([w] * dimension)
            for k in range(dimension):
                s[:,:,k] *= b[i,j,k]
            out += s
    return out

def surface_derivs(b, n=10, u=None, v=None):
    degree1 = b.shape[0] - 1
    degree2 = b.shape[1] - 1
    dimension = b.shape[2]

    '''
    S(u, v) = sum_i^n ( sum_j^m ( B_i^n(u) * B_j^m(v) * P_ij )
            = sum_i^n ( sum_j^m ( comb(n, i) * u^i * (1 - u)^(n - i) * B_j^m(v) * P_ij )

      u^i * (1 - u)^(n - i)
      i * u^(i-1) * (1 - u)^(n - i) + u^i (d/du (1-u)^(n - i))
      i * u^(i-1) * (1 - u)^(n - i) + u^i (d/du (1-u)^(n - i))
      i * u^(i-1) * (1 - u)^(n - i) - u^i (n - i) (1-u)^(n - i - 1)
      (1 - u) * i * u^(i-1) * (1 - u)^(n - i - 1) - u^i (n - i) (1-u)^(n - i - 1)
      ((1 - u) * i - u *  (n - i)) u^(i - 1) (1-u)^(n - i - 1)
      ((i - ui - un + iu) u^(i - 1) (1-u)^(n - i - 1)
      ((i  - un) u^(i - 1) (1-u)^(n - i - 1)

      u^(i-1) * (1 - u)^(n - i - 1) * (i - n * u)


      dS/du = sum_i^n ( sum_j^m ( comb(n, i) * u^i * (1 - u)^(n - i) * B_j^m(v) * P_ij )
    '''

    if u is None:
        u = np.linspace(0, 1, n)
    elif isinstance(u, float):
        u = np.array([u])
    if v is None:
        v = np.linspace(0, 1, n)
    elif isinstance(v, float):
        v = np.array([v])

    d_du = np.zeros([len(u), len(v), dimension])
    d_dv = np.zeros([len(u), len(v), dimension])
    for i in range(degree1 + 1):
        for j in range(degree1 + 1):
            wu = bernstein_deriv(i, degree1, u)
            wv = bernstein(j, degree1, v)
            w = wu.reshape(-1,1).dot(wv.reshape(1,-1))
            s = np.dstack([w] * dimension)
            for k in range(dimension):
                s[:,:,k] *= b[i,j,k]
            d_du += s

            wu = bernstein(i, degree1, u)
            wv = bernstein_deriv(j, degree1, v)
            w = wu.reshape(-1,1).dot(wv.reshape(1,-1))
            s = np.dstack([w] * dimension)
            for k in range(dimension):
                s[:,:,k] *= b[i,j,k]
            d_dv += s
    norms = np.cross(d_dv.reshape(-1, 3), d_du.reshape(-1, 3))
    return norms / np.linalg.norm(norms, axis=1).reshape(-1, 1)


def parse_bpt(data):
    ''' Parses a BPT file, which is a primitive B-rep format

        Returns a list of patches
    '''
    lines = data.split('\n')
    count = int(lines[0])
    i = 1
    patches = []
    for _ in range(count):
        (n, m) = map(int, lines[i].split(' '))
        i += 1
        patch = []
        for _ in range(n + 1):
            row = []
            for _ in range(m + 1):
                row.append(list(map(float, lines[i].split(' '))))
                i += 1
            patch.append(row)
        patches.append(np.array(patch))
    return patches

def S_v(b, v=None):
    ''' Builds the S_v matrix using the equation on p4
    '''
    degree1 = b.shape[0] - 1
    degree2 = b.shape[1] - 1
    dimension = b.shape[2]
    if v == None:
        # Pick a v that ensures the drop-of-rank property, based on Section 3.2
        v = (2 * min(degree1, degree2) - 1, max(degree1, degree2) - 1)

    stride = (v[0] + 1) * (v[1] + 1)
    out = np.zeros(((degree1 + v[0] + 1) * (degree2 + v[1] + 1),
                    4 * stride))
    for axis in range(dimension + 1):
        if axis == 0:
            c = np.ones_like(b[:,:,axis])
        else:
            c = b[:,:,axis - 1]
        for k in range(v[0] + 1):
            v_k = comb(v[0], k)
            for l in range(v[1] + 1):
                v_l = comb(v[1], l)
                for i in range(degree1 + 1):
                    for j in range(degree2 + 1):
                        # B_{i+k} * B_{j+l}
                        row = (j + l) + (i + k) * (v[1] + degree2 + 1)
                        out[row, l + k * (v[1] + 1) + axis * stride] += \
                            v_k * v_l * comb(degree1, i) * comb(degree2, j) \
                            / (comb(v[0] + degree1, i + k) * comb(v[1] + degree2, j + l)) \
                            * c[i,j]
    return out

def build_M(b):
    ''' Builds a generator function that takes X, Y, Z and returns M

        b are control points on a Bézier surface
    '''
    s = S_v(b)
    null = null_space(s)
    i = int(null.shape[0] / 4)
    return lambda x,y,z: \
        null[:i,:] + null[i:2*i,:] * x \
                   + null[2*i:3*i,:] * y \
                   + null[3*i:4*i,:] * z

def parameterize_ray(M, o, d):
    ''' Combines a MRep M with a ray R given by an origin o and direction d
        Returns A, B matrices such that M(R(t)) = A - tB
    '''
    A = M(*o)
    B = M(o[0] + d[0], o[1] + d[1], o[2] + d[2]) - A
    return A, B

def draw_patches(patches, n=10):
    ''' Draws a set of B-rep patches as a point cloud
    '''
    fig = plt.figure()
    ax = fig.add_subplot(projection='3d')
    bounds = []
    for p in patches:
        samples = sample_surface(p, n)
        x = samples[:,:,0]
        y = samples[:,:,1]
        z = samples[:,:,2]
        bounds.append([np.min(x), np.min(y), np.min(z), np.max(x), np.max(y), np.max(z)])
        ax.scatter(x, y, z)
    bounds = np.array(bounds)
    mins = np.min(bounds[:,:3], axis=0)
    maxs = np.max(bounds[:,3:], axis=0)
    scale = np.max(maxs - mins)
    centers = (mins + maxs) / 2

    ax.set_xlim(centers[0] - scale, centers[0] + scale)
    ax.set_ylim(centers[1] - scale, centers[1] + scale)
    ax.set_zlim(centers[2] - scale, centers[2] + scale)
    plt.show()

def reduce_pencil_easy(A, B):
    ''' oh no how did I get here I'm not good with computer
    '''
    while True:
        (u1, e1, vt1) = np.linalg.svd(B)
        tol = e1.max(axis=-1, keepdims=True) * max(B.shape[-2:]) * np.core.finfo(e1.dtype).eps
        if np.sum(e1 > tol) == B.shape[1]:
            break
        r = np.sum(e1 > tol)
        print("Got r", r)

        bv1 = np.matmul(B, vt1.T)
        i = np.min(np.where(np.max(np.abs(bv1), axis=0) < 1e-8))
        assert(r == i)
        av1 = np.matmul(A, vt1.T)
        A1 = av1[:,i:]
        (u2, e2, vt2) = np.linalg.svd(A1)
        print("e2:", e2)
        A = np.matmul(np.matmul(u2.T, A), vt1.T)
        B = np.matmul(np.matmul(u2.T, B), vt1.T)
        mask = np.abs(A) < 1e-8
        if mask.sum() == 0:
            return False
        mask = np.where(mask)
        i = mask[0][0]
        j = mask[1][0]
        A = A[i:,:j]
        B = B[i:,:j]
        if len(B.ravel()) == 0:
            return False
        print(A.shape)
    if B.shape[0] == B.shape[1]:
        return A, B
    else:
        return reduce_pencil_easy(A.T, B.T)

def pencil_eigenvalues(A, B):
    out = reduce_pencil_easy(A, B)
    if out:
        A, B = out
        eigs = eigvals(A, B)
        return eigs
    else:
        return []
        # https://arxiv.org/pdf/1805.07657.pdf is another alternative, maybe
        # faster than GUPTRI but requires you to put the matrix into KCF form
        # yourself, and I don't have time for that!
        S, T, P, Q, kstr = guptri(A, B)
        blocks = np.cumsum(kcf_blocks(kstr), axis=1).astype(int)
        S = S[blocks[0,1]:blocks[0,2], blocks[1,1]:blocks[1,2]]
        T = T[blocks[0,1]:blocks[0,2], blocks[1,1]:blocks[1,2]]
        return S.diagonal() / T.diagonal()

def preimages(M, P):
    ''' Calculates the pre-image of the point P given an M-rep M

        This uses the original M-Rep paper, not the later ray-tracing
        paper, because the latter is inexplicable.  As such, it's not as
        robust and doesn't account for multiple pre-images.
    '''
    # Use last column of SVD to approximate null space of M_v(P)^T
    (u,_,_) = np.linalg.svd(M(*P))
    n = u[:,-1]

    # Hard-coded ratios based on the v used for our patches
    v = (5, 2)
    # Use least-squares to robustly solve for parameters
    A = np.hstack([v[1] * n[0::v[1]+1] + n[1::v[1]+1],
                   v[1] * n[v[1]::v[1] + 1] + n[v[1] - 1::v[1] + 1]])
    print("A SIZE", A.shape)
    B = np.hstack([n[1::v[1] + 1], v[1] * n[v[1]::v[1] + 1]])
    u = np.linalg.lstsq(A.reshape(-1, 1), B.reshape(-1, 1), rcond=None)[0][0]

    A = np.hstack([v[0] * n[0:v[1] + 1] + n[v[1] + 1:2*(v[1] + 1)],
                   v[0] * n[-v[1] - 1:] + n[-2*(v[1] + 1): -(v[1] + 1)]])
    print("A SIZE", A.shape)
    B = np.hstack([n[v[1] + 1:2*(v[1] + 1)], v[0] * n[-v[1] - 1:]])
    v = np.linalg.lstsq(A.reshape(-1, 1), B.reshape(-1, 1), rcond=None)[0][0]

    eps = 1e-8
    if u >= -eps and u <= 1 + eps and v >= -eps and v <= 1 + eps:
        return (u, v)
    else:
        return False

def raytrace(ray_origin, ray_dir, implicit_patches):
    ''' Raytraces from the origin in the given direction, finding the
        nearest collision against a set of implicit patches.
    '''
    min_dist = 1e12
    hit_index = None
    hit_uv = None

    if isinstance(ray_origin, list):
        ray_origin = np.array(ray_origin)
    if isinstance(ray_dir, list):
        ray_dir = np.array(ray_dir)

    eps = 1e-8

    targets = []
    for (i, (M, bounds_min, bounds_max)) in enumerate(implicit_patches):
        box_dist = ray_box(ray_origin, ray_dir, bounds_min, bounds_max)
        if box_dist is None:
            continue
        else:
            targets.append((box_dist, i, M, bounds_min, bounds_max))
    targets.sort()

    actual_search = 0
    for (box_dist, index, M, bounds_min, bounds_max) in targets:
        if box_dist > min_dist:
            continue
        actual_search += 1
        eigs = pencil_eigenvalues(*parameterize_ray(M, ray_origin, ray_dir))
        for e in eigs:
            # Skip imaginary points points
            if abs(e.imag) > 1e-8:
                continue

            # Skip points that are farther than our nearest existing hit
            dist = -e.real
            if dist < 0:
                continue
            if dist > min_dist:
                continue
            pt = ray_origin + ray_dir * dist

            # Skip points that are outside the patch bounding box
            if not np.all((pt >= bounds_min - eps) * (pt <= bounds_max + eps)):
                continue

            uv = preimages(M, pt)
            if uv is False:
                continue

            # We've found a hit, a palpable hit!
            min_dist = dist
            hit_index = index
            hit_uv = uv
    return min_dist, hit_index, hit_uv, len(targets), actual_search

# C function to accelerate ray-box testing
import ctypes
from ctypes.util import find_library
raybox_lib = ctypes.cdll.LoadLibrary(find_library('raybox'))
DOUBLE_PTR = ctypes.POINTER(ctypes.c_double)
raybox_lib.ray_box.argtypes = [DOUBLE_PTR]*5
raybox_lib.ray_box.restype = ctypes.c_bool

def ray_box(ray_origin, ray_dir, box_min, box_max):
    ''' Checks a ray-box intersection.  Returns (distance, hit position),
        which are both None if no intersection occurs.
    '''
    res = ctypes.c_double(0.0)
    assert(ray_origin.dtype == np.float64)
    assert(ray_dir.dtype == np.float64)
    assert(box_min.dtype == np.float64)
    assert(box_max.dtype == np.float64)
    out = raybox_lib.ray_box(
        ctypes.cast(ray_origin.ctypes.data, DOUBLE_PTR),
        ctypes.cast(ray_dir.ctypes.data, DOUBLE_PTR),
        ctypes.cast(box_min.ctypes.data, DOUBLE_PTR),
        ctypes.cast(box_max.ctypes.data, DOUBLE_PTR),
        res)
    if out:
        return res.value
    else:
        return None

def prepare(patches):
    ''' Packs a set of explicit patches into tuples
            (implicit patch, min, max)
        Returns a list of said tuples
    '''
    out = []
    for p in patches:
        M = build_M(p)

        bounds_min = p.reshape(-1, 3).min(axis=0)
        bounds_max = p.reshape(-1, 3).max(axis=0)
        out.append((M, bounds_min, bounds_max))
    return out

with open('../teapot.bpt') as f:
    patches = parse_bpt(f.read())
pt = np.copy(patches[0][0,0,:])
mrep = build_M(patches[0])
dir = np.array([0,0,1])
pt -= dir
A, B = parameterize_ray(mrep, pt, dir)
reduce_pencil_easy(A, B)
preimages(mrep, patches[0][0,0,:])

from __future__ import division

import math
from copy import deepcopy
from numbers import Number

import numpy as np
import meep as mp


def check_nonnegative(prop, val):
    if val >= 0:
        return val
    else:
        raise ValueError("{} cannot be negative. Got {}".format(prop, val))


class Vector3(object):

    def __init__(self, x=0.0, y=0.0, z=0.0):
        self.x = float(x) if type(x) is int else x
        self.y = float(y) if type(y) is int else y
        self.z = float(z) if type(z) is int else z

    def __eq__(self, other):
        return self.x == other.x and self.y == other.y and self.z == other.z

    def __add__(self, other):
        x = self.x + other.x
        y = self.y + other.y
        z = self.z + other.z

        return Vector3(x, y, z)

    def __sub__(self, other):
        x = self.x - other.x
        y = self.y - other.y
        z = self.z - other.z

        return Vector3(x, y, z)

    def __mul__(self, other):
        if type(other) is Vector3:
            return self.dot(other)
        elif isinstance(other, Number):
            return self.scale(other)
        else:
            raise TypeError("No operation known for 'Vector3 * {}'".format(type(other)))

    def __rmul__(self, other):
        if isinstance(other, Number):
            return self.scale(other)
        else:
            raise TypeError("No operation known for '{} * Vector3'".format(type(other)))

    def __getitem__(self, i):
        if i == 0:
            return self.x
        elif i == 1:
            return self.y
        elif i == 2:
            return self.z
        else:
            raise IndexError("No value at index {}".format(i))

    def __repr__(self):
        return "Vector3<{}, {}, {}>".format(self.x, self.y, self.z)

    def __array__(self):
        return np.array([self.x, self.y, self.z])

    def scale(self, s):
        x = self.x * s
        y = self.y * s
        z = self.z * s

        return Vector3(x, y, z)

    def dot(self, v):
        return self.x * v.x + self.y * v.y + self.z * v.z

    def cdot(self, v):
        conj_vec = Vector3(self.x.conjugate(),
                           self.y.conjugate(),
                           self.z.conjugate())
        return conj_vec.dot(v)

    def cross(self, v):
        x = self.y * v.z - self.z * v.y
        y = self.z * v.x - self.x * v.z
        z = self.x * v.y - self.y * v.x

        return Vector3(x, y, z)

    def norm(self):
        return math.sqrt(abs(self.dot(self)))

    def unit(self):
        return self.scale(1 / self.norm())

    def close(self, v, tol=1.0e-7):
        return (abs(self.x - v.x) <= tol and
                abs(self.y - v.y) <= tol and
                abs(self.z - v.z) <= tol)

    def rotate(self, axis, theta):
        u = axis.unit()
        vpar = u.scale(u.dot(self))
        vcross = u.cross(self)
        vperp = self - vpar
        return vpar + (vperp.scale(math.cos(theta)) + vcross.scale(math.sin(theta)))


class Medium(object):

    def __init__(self, epsilon_diag=Vector3(1, 1, 1),
                 epsilon_offdiag=Vector3(),
                 mu_diag=Vector3(1, 1, 1),
                 mu_offdiag=Vector3(),
                 E_susceptibilities=[],
                 H_susceptibilities=[],
                 E_chi2_diag=Vector3(),
                 E_chi3_diag=Vector3(),
                 H_chi2_diag=Vector3(),
                 H_chi3_diag=Vector3(),
                 D_conductivity_diag=Vector3(),
                 B_conductivity_diag=Vector3(),
                 epsilon=None,
                 index=None,
                 mu=None,
                 chi2=None,
                 chi3=None,
                 D_conductivity=None,
                 B_conductivity=None,
                 E_chi2=None,
                 E_chi3=None,
                 H_chi2=None,
                 H_chi3=None):

        if epsilon:
            epsilon_diag = Vector3(epsilon, epsilon, epsilon)
        elif index:
            i2 = index * index
            epsilon_diag = Vector3(i2, i2, i2)

        if mu:
            mu_diag = Vector3(mu, mu, mu)

        if D_conductivity:
            D_conductivity_diag = Vector3(D_conductivity, D_conductivity, D_conductivity)
        if B_conductivity:
            B_conductivity_diag = Vector3(B_conductivity, B_conductivity, B_conductivity)

        if E_chi2:
            E_chi2_diag = Vector3(E_chi2, E_chi2, E_chi2)
        if E_chi3:
            E_chi3_diag = Vector3(E_chi3, E_chi3, E_chi3)
        if H_chi2:
            H_chi2_diag = Vector3(H_chi2, H_chi2, H_chi2)
        if H_chi3:
            H_chi3_diag = Vector3(H_chi3, H_chi3, H_chi3)

        self.epsilon_diag = epsilon_diag
        self.epsilon_offdiag = epsilon_offdiag
        self.mu_diag = mu_diag
        self.mu_offdiag = mu_offdiag
        self.E_susceptibilities = E_susceptibilities
        self.H_susceptibilities = H_susceptibilities
        self.E_chi2_diag = Vector3(chi2, chi2, chi2) if chi2 else E_chi2_diag
        self.E_chi3_diag = Vector3(chi3, chi3, chi3) if chi3 else E_chi3_diag
        self.H_chi2_diag = H_chi2_diag
        self.H_chi3_diag = H_chi3_diag
        self.D_conductivity_diag = D_conductivity_diag
        self.B_conductivity_diag = B_conductivity_diag


class Susceptibility(object):

    def __init__(self, sigma_diag=Vector3(), sigma_offdiag=Vector3(), sigma=None):
        self.sigma_diag = mp.Vector3(sigma, sigma, sigma) if sigma else sigma_diag
        self.sigma_offdiag = sigma_offdiag


class LorentzianSusceptibility(Susceptibility):

    def __init__(self, frequency=0.0, gamma=0.0, **kwargs):
        super(LorentzianSusceptibility, self).__init__(**kwargs)
        self.frequency = frequency
        self.gamma = gamma


class DrudeSusceptibility(Susceptibility):

    def __init__(self, frequency=0.0, gamma=0.0, **kwargs):
        super(DrudeSusceptibility, self).__init__(**kwargs)
        self.frequency = frequency
        self.gamma = gamma


class NoisyLorentzianSusceptibility(LorentzianSusceptibility):

    def __init__(self, noise_amp=0.0, **kwargs):
        super(NoisyLorentzianSusceptibility, self).__init__(**kwargs)
        self.noise_amp = noise_amp


class NoisyDrudeSusceptibility(DrudeSusceptibility):

    def __init__(self, noise_amp=0.0, **kwargs):
        super(NoisyDrudeSusceptibility, self).__init__(**kwargs)
        self.noise_amp = noise_amp


class GeometricObject(object):

    def __init__(self, material=Medium(), center=Vector3(), epsilon_func=None):
        if type(material) is not Medium and callable(material):
            material.eps = False
        elif epsilon_func:
            epsilon_func.eps = True
            material = epsilon_func

        self.material = material
        self.center = center

    def __contains__(self, point):
        return mp.is_point_in_object(point, self)

    def __add__(self, vec):
        self.center += vec

    def shift(self, vec):
        self.center += vec

    def info(self, indent_by=0):
        mp.display_geometric_object_info(indent_by, self)


class Sphere(GeometricObject):

    def __init__(self, radius, **kwargs):
        self.radius = float(radius)
        super(Sphere, self).__init__(**kwargs)

    @property
    def radius(self):
        return self._radius

    @radius.setter
    def radius(self, val):
        self._radius = check_nonnegative("Sphere.radius", val)


class Cylinder(GeometricObject):

    def __init__(self, radius, axis=Vector3(0, 0, 1), height=1e20, **kwargs):
        self.axis = axis
        self.radius = float(radius)
        self.height = float(height)
        super(Cylinder, self).__init__(**kwargs)

    @property
    def radius(self):
        return self._radius

    @property
    def height(self):
        return self._height

    @radius.setter
    def radius(self, val):
        self._radius = check_nonnegative("Cylinder.radius", val)

    @height.setter
    def height(self, val):
        self._height = check_nonnegative("Cylinder.height", val)


class Wedge(Cylinder):

    def __init__(self, radius, wedge_angle=2 * math.pi, wedge_start=Vector3(1, 0, 0), **kwargs):
        self.wedge_angle = wedge_angle
        self.wedge_start = wedge_start
        super(Wedge, self).__init__(radius, **kwargs)


class Cone(Cylinder):

    def __init__(self, radius, radius2=0, **kwargs):
        self.radius2 = radius2
        super(Cone, self).__init__(radius, **kwargs)


class Block(GeometricObject):

    def __init__(self, size, e1=Vector3(1, 0, 0), e2=Vector3(0, 1, 0), e3=Vector3(0, 0, 1), **kwargs):
        self.size = size
        self.e1 = e1
        self.e2 = e2
        self.e3 = e3
        super(Block, self).__init__(**kwargs)


class Ellipsoid(Block):

    def __init__(self, **kwargs):
        super(Ellipsoid, self).__init__(**kwargs)


def geometric_object_duplicates(shift_vector, min, max, *objs):
    dups = []
    for obj in objs:
        for i in range(min, max + 1):
            o = deepcopy(obj)
            o.shift(shift_vector.scale(i))
            dups.append(o)

    return dups

from numpy import zeros
from numpy import hstack
from numpy import vstack
from numpy import array
from numpy.linalg import inv
from cv2 import Rodrigues
from cv2 import projectPoints


class Device:

    default_scale = 1
    default_translation = zeros((1, 3), dtype='float')
    default_rotation = zeros((1, 3), dtype='float')

    devs = {}

    def __init__(self, name='device', translation=None, rotation=None, scale=None):

        self.name = name

        self.devs[self.name] = self

        self.scale = scale if scale else self.default_scale

        self._rotation = array(rotation).reshape(1, 3) / self.scale if rotation else self.default_rotation
        self._translation = array(translation).reshape(1, 3) / self.scale if translation else self.default_translation
        self.update_rotation_matrix()
        self.update_extrinsic_matrix()

    @property
    def translation(self):
        self._translation = None

    @translation.getter
    def translation(self):
        return self._translation

    @translation.setter
    def translation(self, value):
        self._translation = array(value).reshape(1, 3)
        self.update_extrinsic_matrix()

    @property
    def rotation(self):
        self._rotation = None
        self.rotation_matrix = None

    @rotation.getter
    def rotation(self):
        return self._rotation

    @rotation.setter
    def rotation(self, value):
        self._rotation = value.reshape(1, 3)
        self.update_rotation_matrix()
        self.update_extrinsic_matrix()

    @staticmethod
    def create_rotation_matrix(rotation):
        """(1, 3) -> (3, 3)"""
        return Rodrigues(rotation)[0]

    @staticmethod
    def restore_extrinsic_matrix(rotation_matrix, translation):
        """(3, 3), (1, 3), (4,) -> (4, 4)"""
        return vstack((hstack((rotation_matrix,
                               translation.T)),
                       array([0.0, 0.0, 0.0, 1.0])))

    def update_rotation_matrix(self):
        self.rotation_matrix = self.create_rotation_matrix(self.rotation)

    def update_extrinsic_matrix(self):
        self.extrinsic_matrix = self.restore_extrinsic_matrix(self.rotation_matrix,
                                                              self.translation)

    def vectors_to_self(self, vectors, translation=True):
        """
        (?, 3) -> (?, 3)

        (inv((3, 3)) @ ( (?, 3) - (1, 3) ).T).T -> (?, 3)
        """
        assert vectors.ndim == 2
        assert vectors.shape[1] == 3
        
        if translation:
            return (inv(self.rotation_matrix) @ (vectors - self.translation).T).T
        else:
            return (inv(self.rotation_matrix) @ vectors.T).T
        
    def vectors_to_origin(self, vectors, translation=True):
        """
        (?, 3) -> (?, 3)

        (inv((3, 3)) @ ( (?, 3) - (1, 3) ).T).T -> (?, 3)
        """
        assert vectors.ndim == 2
        assert vectors.shape[1] == 3
        
        if translation:
            return (self.rotation_matrix @ vectors.T + self.translation.T).T
        else:
            return (self.rotation_matrix @ vectors.T).T

    @classmethod
    def get(cls, name):
        return cls.devs.get(name)

    @classmethod
    def pop(cls, name):
        cls.devs.pop(name)

    @classmethod
    def clear(cls):
        cls.devs = {}

    @classmethod
    def items(cls):
        return cls.devs.items()

    @classmethod
    def keys(cls):
        return cls.devs.keys()

    @classmethod
    def values(cls):
        return cls.devs.values()

class Camera(Device):

    default_matrix = zeros((3, 3), dtype='float')
    default_distortion = zeros((4,), dtype='float')

    def __init__(self, name='camera', translation=None, rotation=None, matrix=None, distortion=None, scale=None):
        super().__init__(name, translation=translation, rotation=rotation)

        self.matrix = array(matrix) if matrix else self.default_matrix
        self.distortion = array(distortion) if distortion else self.default_distortion

    def project_vectors(self, vectors):
        return projectPoints(vectors,
                             -self.rotation,
                             -(inv(self.rotation_matrix) @ self.translation.T),
                             self.matrix,
                             self.distortion)[0].reshape(-1, 2)

    def find_ray_point(self, image_points, origin=True):
        """
        ((3, 3) @ (?, 3).T).T -> (?, 3)
        """

        assert image_points.ndim == 2
        assert image_points.shape[1] == 3

        ray_points = (inv(self.matrix) @ image_points.T).T
        return self.vectors_to_origin(ray_points) if origin else ray_points


import unittest
import random

import  risk.state.board_generator as bg

class TestCreatingBoard(unittest.TestCase):

    def test_initial_polygon_creation(self):
       
        dims = (1000, 800)
        polygon = bg.create_polygon_to_fill_space(dims, portion=0.75)
        validation = polygon.validate_vertices()
        self.assertTrue(validation['is_valid'])

    def test_initial_polygon_creation_size(self):
        dims = (1000, 800)
        portion = 0.75
        polygon = bg.create_polygon_to_fill_space(dims, portion=portion)
        area = polygon.area()
        self.assertTrue(area <= dims[0] * dims[1] * portion)

    def test_mass_polygon_creation(self):
        dims = (1000, 800)
        portion = 0.75
        for i in range(25):
            polygon = bg.create_polygon_to_fill_space(dims, portion=portion)
            validation = polygon.validate_vertices()
            self.assertTrue(validation['is_valid'])
            area = polygon.area()
            self.assertTrue(area <= dims[0] * dims[1] * portion)

    def test_subdivision(self):
        dims = (1000, 800)
        portion = 0.75
        polygon = bg.create_polygon_to_fill_space(dims, portion=portion)
        left, right = polygon.divide()
        self.assertIsNotNone(left)
        self.assertIsNotNone(right)
        self.assertTrue(left.validate_vertices()['is_valid'])
        self.assertTrue(right.validate_vertices()['is_valid'])
        self.assertNotEqual(left, right)
        self.assertTrue(polygon.is_divided)
        self.assertLessEqual(left.area() + right.area(), polygon.area() * 1.5)

    def test_mass_subdivision(self):
        portion = 0.75
        for i in range(25):
            dims = (random.randint(500, 1500), random.randint(400, 1200))
            polygon = bg.create_polygon_to_fill_space(dims, portion=portion)
            left, right = polygon.divide()
            self.assertIsNotNone(left)
            self.assertIsNotNone(right)
            self.assertTrue(left.validate_vertices()['is_valid'])
            self.assertTrue(right.validate_vertices()['is_valid'])
            self.assertNotEqual(left, right)
            self.assertTrue(polygon.is_divided)
            self.assertLessEqual(left.area() + right.area(), polygon.area() * 1.5)

import unittest

from risk.state.event_stack import Event, Level, EventStack

class TestEvents(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_create(self):
        ev = Event("attack")
        ev2 = Event("defend")
        ev3 = Event("attack")
        ev4 = Event("attack", { 'p1' : 1}) 

        with self.assertRaises(TypeError):
            ev.id = "foo"
        with self.assertRaises(AttributeError):
            ev.context.foo
        with self.assertRaises(TypeError):
            ev.context.bar = 2

    def test_eq(self):
        ev = Event("attack")
        ev2 = Event("defend")
        ev3 = Event("attack")
        ev4 = Event("attack", { 'p1' : 1}) 

        self.assertTrue(ev != ev2)
        self.assertTrue(ev == ev)
        self.assertTrue(ev == ev3)
        self.assertTrue(ev4 != ev)
        self.assertTrue(ev4 != ev2)
        self.assertTrue(ev4 != ev3)
        self.assertTrue(ev4.context.p1 == 1)

    def test_str(self):
        ev = Event("attack")
        self.assertEqual(str(ev), "Event: attack, Context: {}")

        ev = Event("attack", dict(launch="now"))
        self.assertEqual(str(ev), f"Event: attack, Context: {str({'launch': 'now'})}")

    def test_hash(self):
        ev = Event("attack")
        ev2 = Event("defend")

        holder = {
            ev : "foo",
            ev2 : "bar"
        }

        self.assertTrue(ev in holder)
        self.assertTrue(ev2 in holder)
        self.assertEqual(holder[ev], "foo")
        self.assertEqual(holder[ev2], "bar")

    def test_repr(self):
        ev = Event("attack")
        ev4 = Event("defend", { 'p1' : 1}) 

        self.assertEqual(eval(repr(ev)), ev)
        self.assertEqual(eval(repr(ev4)), ev4)
    

class TestLevel(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_create(self):
        
        turn_one = Level("Turn 1")

        with self.assertRaises(TypeError):
            turn_one.id = "foo"
        with self.assertRaises(TypeError):
            turn_one["bar"] = "baz"

    def test_eq(self):

        turn_one = Level("Turn 1")
        turn_one_b = Level("Turn 1")

        turn_two = Level("Turn 2") 

        self.assertNotEqual(turn_one, turn_two)
        self.assertEqual(turn_one, turn_one_b)

    def test_repr(self):

        turn_one = Level("Turn 1")

        self.assertEqual(turn_one, eval(repr(turn_one)))

    def test_hash(self):

        turn_one = Level("Turn 1")
        turn_two = Level("Turn 2")

        holder = {
            turn_one : "foo",
            turn_two : "bar"
        }

        self.assertTrue(turn_one in holder)
        self.assertTrue(turn_two in holder)
        self.assertEqual(holder[turn_one], "foo")
        self.assertEqual(holder[turn_two], "bar")

    def test_collide(self):

        turn_one = Level("Turn 1")
        event = Event("Turn 1")

        self.assertNotEqual(turn_one, event)
        self.assertNotEqual(turn_one.id, event.id)

class TestEventStack(unittest.TestCase):

    def test_create(self):
        stack = EventStack("Game Loop")

        with self.assertRaises(TypeError):
            stack.foo = "bar"
        with self.assertRaises(TypeError):
            stack['baz'] = 2
        with self.assertRaises(TypeError):
            stack.id = 2

    def test_push(self):
        ev = Event("event 1")
        ev2 = Event("event 2")
        ev3 = Event("event 3")

        stack = EventStack("loop")

        self.assertEqual(len(stack), 0)
        stack.push(ev)
        self.assertEqual(len(stack), 1)
        stack.push(ev2)
        self.assertEqual(len(stack), 2)
        stack.push(ev3)
        self.assertEqual(len(stack), 3)
        self.assertEqual(stack.peek(), ev3)

    def test_pop(self):
        ev = Event("event 1")
        ev2 = Event("event 2")
        ev3 = Event("event 3")

        stack = EventStack("loop")
        stack.push(ev)
        stack.push(ev2)
        stack.push(ev3)

        self.assertEqual(len(stack), 3)
        out = stack.pop()
        self.assertEqual(out, ev3)
        self.assertEqual(len(stack), 2)
        out = stack.pop()
        self.assertEqual(out, ev2)
        self.assertEqual(len(stack), 1)
        out = stack.pop()
        self.assertEqual(out, ev)
        self.assertEqual(len(stack), 0)
        out = stack.pop()
        self.assertEqual(out, None)

    def test_level(self):
        ev = Event("event 1")
        level_one = Level("Turn 1")
        ev2 = Event("event 2")
        ev3 = Event("event 3")
        level_two = Level("Turn 2")
        ev4 = Event("event 4")

        stack = EventStack("loop")
        out = stack.current_level
        self.assertEqual(out, None)

        stack.push(ev)
        stack.push(level_one)
        out = stack.current_level
        self.assertEqual(out, level_one)

        stack.push(ev2)
        stack.push(ev3)
        stack.push(level_two)
        out = stack.current_level
        self.assertEqual(out, level_two)

        stack.push(ev4)
        stack.pop()
        stack.pop()
        out = stack.current_level
        self.assertEqual(out, level_one)

    def test_depth(self):
        ev = Event("event 1")
        level_one = Level("Turn 1")
        ev2 = Event("event 2")
        ev3 = Event("event 3")
        level_two = Level("Turn 2")

        stack = EventStack("loop")
        self.assertEqual(stack.depth, 0)

        stack.push(ev)
        stack.push(level_one)
        self.assertEqual(stack.depth, 1)

        stack.push(ev2)
        stack.push(ev3)
        stack.push(level_two)
        self.assertEqual(stack.depth, 2)

        stack.pop()
        self.assertEqual(stack.depth, 1)

        stack.pop()
        stack.pop()
        stack.pop()
        self.assertEqual(stack.depth, 0)

    def test_substack(self):
        ev = Event("event 1")
        level_one = Level("Turn 1")
        ev2 = Event("event 2")
        ev3 = Event("event 3")
        level_two = Level("Turn 2")

        stack = EventStack("loop")

        stack.push(ev)
        stack.push(level_one)
        new_stack = stack.substack(stack.size)
        self.assertEqual(new_stack.current_level, stack.current_level)
        self.assertNotEqual(new_stack, stack)
        self.assertNotEqual(stack.substack(-1).current_level, stack.current_level)

        stack.push(ev2)
        stack.push(ev3)
        stack.push(level_two)
        new_stack = stack.substack(stack.size)
        self.assertEqual(new_stack.current_level, stack.current_level)
        self.assertNotEqual(new_stack, stack)
        self.assertNotEqual(stack.substack(-1).current_level, stack.current_level)
        self.assertEqual(stack.substack(-1).current_level, level_one)

    def test_collide(self):
        event_one = Event("turn one")
        level_one = Level("turn one")
        stack = EventStack("turn one")

        self.assertNotEqual(event_one.id, stack.id)
        self.assertNotEqual(level_one.id, stack.id) 


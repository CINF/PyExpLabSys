import parallel

class ParallelPortBinaryOut:
    """ Used to manually set the state of the 8 binary pins in a parallel port
    """
    def __init__(self, port=0):
        self.parallel = parallel.Parallel(port=port)
        # list of states, port number are equal to list index, endianness is
        # handled in the setStates function
        self.state = [False]*8

    def setState(self, port=0, active=False):
        """ Set the state of to the boolean value of an input

        Keyword arguments
        port   -- The port number (0-7)
        active -- The new state (True or False) or anything whose boolean value
                  can be intertreted by "bool()"
        """
        if not (0 <= port <= 7):
            raise Exception('Port number must be between 0 and 7')

        # Interprete the boolean value of "active" and set the state
        active = bool(active)
        self.state[port] = active
        self._update_hardware()

    def _update_hardware(self):
        """ Write the list of boolean values to the hardware """
        # Reverse for correct endianness. Turn True and False into '1' and '0'
        state = [str(int(element)) for element in reversed(self.state)]
        # Combine into string and convert binary string to number
        state = int(''.join(state), 2)
        self.parallel.setData(state)
        
if __name__ == "__main__":
    p = ParallelPortBinaryOut()

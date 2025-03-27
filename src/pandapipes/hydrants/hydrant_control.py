# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd

from pandapipes.pf.pipeflow_setup import get_fluid
from pandapipes.constants import NORMAL_TEMPERATURE
from pandapower.control.basic_controller import Controller
from pandapipes.hydrants.config import MODE
if MODE == "junction":
    from pandapipes.hydrants.hydrant_on_junction.hydrant_on_junction_creation import set_hydrant_flow
elif MODE == "pipe":
    from pandapipes.hydrants.hydrant_on_pipe.hydrant_on_pipe_creation import set_hydrant_flow
else: raise ImportError("You did not import the hydrants module correctly, use either import pandapipes.hydrants.hydrant_on_junction or import pandapipes.hydrants.hydrant_on_pipe")


class HydrantControlFlow(Controller):
    '''
    The Base controller for hydrants.
    '''
    def __init__(self, net, hydrant, p_min = 1.5,
                 in_service=True, order=0, level=0, **kwargs):
        '''
        The Base controller for hydrants.

        :param net: The pandapipes network
        :type net: pandapipesNet
        :param hydrant: The index of the hydrant.
        :type hydrant: int
        :param p_min: The minimal pressure in the grid
        :type p_min: float, default 1.5
        :param kwargs: Additional keyword arguments
        :type kwargs: dict
        :return: No output
        '''
        super().__init__(net, in_service=in_service, order=order, level=level, initial_run=True, **kwargs)

        self.hydrant = hydrant

        self.p_min = p_min 
        self.p = 0

        self.result_index = ["index_junction", "name_hydrant", "mdot_kg_per_s", "vdot_m3_per_h", "p_bar"]

    def set_hydrant(self, hydrant):
        '''
        Set a new hydrant for the controller.

        :param hydrant: The index of the hydrant.
        :type hydrant: int
        '''
        self.hydrant = hydrant

    def initialize_control(self, net):
        pass    
    
    def restore_init_state(self, net):
        '''
        Restore the initial state of the controller, ie. reset the net.
        '''
        set_hydrant_flow(net, self.hydrant, 0)

    def finalize_control(self, net):
        '''
        When the controller is finished the results (i.e. the mass flow and pressure at the hydrant outflow etc.) are written into the net.
        '''
        self.restore_init_state(net)



class HydrantControlFlowList(HydrantControlFlow):
    '''
    Controller to search for the highest possible flow rate of a hydrant from a given list.
    '''
    def __init__(self, net, hydrant, flow_list = [192, 96, 48, 24, 0], flow_unit = "m3/h", p_min = 1.5,
                 in_service=True, order=0, level=0, **kwargs):
        '''
        The controller to search for the highest possible flow rate at a hydrant from a given list.

        :param net: The pandapipes network
        :type net: pandapipesNet
        :param hydrant: The index of the node where the hydrant should be installed.
        :type hydrant: int
        :param flow_list: The list of flow rates that should be tested.
        :type flow_list: list, default [192, 96, 48, 24, 0]
        :param flow_unit: The unit of the flow rates, can be "m3/h" and "kg/s".
        :type flow_unit: string, default m3/h
        :param p_min: The minimal pressure in the grid
        :type p_min: float, default 1.5
        :param kwargs: Additional keyword arguments
        :type kwargs: dict
        '''

        super().__init__(net, hydrant, p_min = p_min,
                 in_service=in_service, order=order, level=level, **kwargs)

        self.flow_list = np.sort(flow_list)[::-1] #sort the list from high to low

        if flow_unit == "m3/h":
            self.flow_list = self.flow_list / 3600 * get_fluid(net).get_density(NORMAL_TEMPERATURE)
        elif flow_unit == "kg/s":
            pass
        
        self.i = 0
        self.f = self.flow_list[self.i]  

    def initialize_control(self, net):
        '''
        Give the hydrant a starting mass flow as given in the list.
        '''
        set_hydrant_flow(net, self.hydrant, self.f)


    def control_step(self, net):
        '''
        The next flow rate from the list is written to the sink.
        '''
        self.i += 1
        self.f = self.flow_list[self.i]                        
        set_hydrant_flow(net, self.hydrant, self.f)


    def is_converged(self, net):
        '''
        If the minimal pressure in the grid is higher than the given minimal pressure, we have converged and found our highest flow rate,
        since the flow rates are sorted highest to lowest. 
        '''
        self.p = np.min(net.res_junction.p_bar)
        
        if (self.p > self.p_min):
            return True
        if self.i == len(self.flow_list)-1:
            raise ValueError("There is no flow rate in the list such that the pressure in the grid is bigger than the minimal pressure.")
        return False
    
    def restore_init_state(self, net):
        '''
        The initial state of the controller is restored. 
        In addition to the net we have to reset the position in the list we are currently in.
        '''
        self.i = 0
        self.f = self.flow_list[self.i] 
        super().restore_init_state(net)


class HydrantControlFlowSearch(HydrantControlFlow):
    def __init__(self, net, hydrant, p_min = 1.5, tol = 10**-2,
                 in_service=True, order=0, level=0, **kwargs):
        '''
        The controller to search for the highest possible flow rate at a hydrant such that the pressure in the grid does not go below a given p_min.
        This will be done by a bisection method, we start with a guessed flow of 48.

        :param net: The pandapipes network
        :type net: pandapipesNet
        :param hydrant: The index of the node where the hydrant should be installed.
        :type hydrant: int
        :param p_min: The minimal pressure in the grid
        :type p_min: float, default 1.5
        :param tol: The tolerance with which the pressure should be determined
        :type tol: float, default 1e-2
        :param kwargs: Additional keyword arguments
        :type kwargs: dict
        '''

        super().__init__(net, hydrant, p_min = p_min,
                 in_service=in_service, order=order, level=level, **kwargs)
         
        self.f = 48
        self.f_high = 0
        self.f_low = 0     

        self.tol = tol


    def initialize_control(self, net):
        '''
        Install the hydrant (a pipe and a junction with the given parameters) onto the given junction (done in super class).
        Give the hydrant a starting mass flow.
        '''
        set_hydrant_flow(net, self.hydrant, self.f)

    def control_step(self, net):
        '''
        Calculate the next flow rate.
        At the start we double our flow rate as long as the pressure in the grid is higher than the minimal pressure.
        Then we use the bisection method to calculate the next flow rate.
        '''
        if self.f_high == self.f_low:
            if self.p < self.p_min:
                self.f_high = self.f
                self.f = (self.f_low + self.f_high) / 2
            else:
                self.f = self.f*2
        else:
            if self.p < self.p_min:
                self.f_high = self.f
            else:
                self.f_low = self.f 
            self.f = (self.f_low + self.f_high) / 2
                                
        set_hydrant_flow(net, self.hydrant, self.f)

    def is_converged(self, net):
        '''
        If the current pressure lies in the tolerance range around the minimal pressure in the grid we have converged.
        '''
        self.p = np.min(net.res_junction.p_bar)

        flow_through_pipe = net.res_pipe.mdot_to_kg_per_s.loc[net.hydrant.hydrant_pipe.loc[self.hydrant]]
        if np.isnan(flow_through_pipe): return True #then the hydrant lies on a junction that is not connected to the grid

        if np.abs(self.f -self.f_high) < self.tol:
            return True
        return False
    
    def restore_init_state(self, net):
        '''
        The initial state of the controller is restored. 
        In addition to the net we have to reset the flow rate interval.
        '''
        self.f = 48
        self.f_high = 0
        self.f_low = 0        

        super().restore_init_state(net)


import warnings

import pandas as pd
import numpy as np
from numpy import dtype

from pandapipes.pf.pipeflow_setup import get_fluid
from pandapipes.constants import NORMAL_TEMPERATURE
from pandapipes.component_models.abstract_models.base_component import Component
from pandapipes.component_models.component_toolbox import add_new_component
from pandapipes.component_models.junction_component import Junction
from pandapipes.component_models.pipe_component import Pipe
from pandapipes.create import create_junction, create_pipe_from_parameters, create_sink, _check_junction_element, _check_multiple_junction_elements
from pandapipes.pf.pipeflow_setup import get_lookup
from pandapipes.idx_node import PINIT, TINIT
from pandapipes.idx_branch import MDOTINIT

from pandapower.auxiliary import write_to_net, read_from_net
from pandapower.create import  _get_index_with_check, _get_multiple_index_with_check, _set_entries, _set_multiple_entries




class Hydrant(Component):
    @classmethod
    def table_name(cls):
        return "hydrant"
    
    @classmethod
    def get_component_input(cls):
        """

        :return:
        :rtype:
        """
        return [('name', dtype(object)),
                ('length_km', 'f8'),
                ('diameter_m', 'f8'),
                ('k_mm', 'f8'),
                ('loss_coefficient', 'f8'),
                ('in_service', 'bool'),
                ('hydrant_in_junction', 'u4'),
                ('hydrant_out_junction', 'u4'),
                ('hydrant_pipe', 'u4'),
                ('hydrant_sink', 'u4')]
    
    @classmethod
    def get_result_table(cls, net):
        """

        :param net: The pandapipes network
        :type net: pandapipesNet
        :return: (columns, all_float) - the column names and whether they are all float type. Only
                if False, returns columns as tuples also specifying the dtypes
        :rtype: (list, bool)
        """
        return [("p_bar", 'f8'), 
                ("t_k", 'f8'), 
                ("mdot_kg_per_s", 'f8'), 
                ("vdot_m3_per_h", 'f8'), 
                ("min_p_bar", 'f8'), 
                ("crit_junction", 'u4'), 
                ("crit_p_bar", 'f8')], False
    
    @classmethod
    def extract_results(cls, net, options, branch_results, mode):
        """
        Function that extracts certain results.

        :param net: The pandapipes network
        :type net: pandapipesNet
        :param options:
        :type options:
        :param branch_results:
        :type branch_results:
        :param mode:
        :type mode:
        :return: No Output.
        """
        res_table = net["res_" + cls.table_name()]

        #Pressure results
        i_active_hydrants = read_from_net(net, "hydrant", None, "in_service", flag="all_index")
        active_hydrants = net.hydrant.index[i_active_hydrants]

        j = read_from_net(net, "hydrant", active_hydrants, "hydrant_out_junction")
        i_j = [True if i in j else False for i in net.junction.index]
        f, t = get_lookup(net, "node", "from_to")[Junction.table_name()]

        junction_pit = net["_pit"]["node"][f:t, :]

        res_table["p_bar"].values[i_active_hydrants] = junction_pit[i_j, PINIT]
        res_table["t_k"].values[i_active_hydrants] = junction_pit[i_j, TINIT]

        #Flow results
        p = read_from_net(net, "hydrant", active_hydrants, "hydrant_pipe")
        i_p = [True if i in p else False for i in net.pipe.index]

        f, t = get_lookup(net, "branch", "from_to")[Pipe.table_name()]
        pipe_pit = net["_pit"]["branch"][f:t, :]

        res_table["mdot_kg_per_s"].values[i_active_hydrants] = pipe_pit[i_p, MDOTINIT]
        res_table["vdot_m3_per_h"].values[i_active_hydrants] = pipe_pit[i_p, MDOTINIT] * 3600 / get_fluid(net).get_density(NORMAL_TEMPERATURE)

        #minimal pressure in whole grid (with junctions that should be ignored for hydrant calculation)
        res_table["min_p_bar"].values[i_active_hydrants] = np.nanmin(junction_pit[:, PINIT])

        #critical junction, critical pressure (without junctions that should be ignored for hydrant calculation)
        if "consider_for_hydrant_calculation" in net.junction.columns:
            j_for_hyd = np.where(read_from_net(net, "junction", None, "consider_for_hydrant_calculation", flag="all_index") == True)
            crit_j = j_for_hyd[np.nanargmin(junction_pit[j_for_hyd, PINIT])]
        else:
            crit_j = np.nanargmin(junction_pit[:, PINIT])

        res_table["crit_junction"].values[i_active_hydrants] = crit_j
        res_table["crit_p_bar"].values[i_active_hydrants] = junction_pit[crit_j, PINIT]

def create_hydrant(net, junction, name = None, index = None, length_km = 0.001, diameter_m = 0.08, k_mm = 0.1, loss_coefficient = 0, **kwargs):
    '''
    Adds one hydrant into table net["hydrant"]. At first it is not in service but has to be activated using insert_hydrant_into_grid(net, hydrant).

    :param net: The pandapipes network in which the element should be created
    :type net: pandapipesNet
    :param junction: The index of the junction to which the hydrant is connected.
    :type junction: int
    :param name: The name for this hydrant
    :type name: string, default None
    :param index: Force a specified ID if it is available. If None, the index one higher than the\
            highest already existing index is selected.
    :param length_km: The length of this hydrant, i.e. the hydrant pipe in kilometers.
    :type length_km: float, default 0.001
    :param diameter_m: The diameter for this hydrant, i.e. the hydrant pipe in meters.
    :type diameter_m: string, default 0.08
    :param k_mm: The roughness for this hydrant, i.e. the hydrant pipe in milimeters.
    :type k_mm: float, default 0.1
    :param loss_coefficient: The additional loss coefficient for this hydrant, this could represent for example an additional firehose etc.
    :type loss_coefficient: float, default 0
    :param kwargs: Additional keyword arguments will be added as further columns to the\
            net["hydrant"] table
    :type kwargs: dict
    :return: index - The unique ID of the created element
    :rtype: int
    '''

    add_new_component(net, Hydrant)
    
    _check_junction_element(net, junction)
    index = _get_index_with_check(net, "hydrant", index)

    cols = ["name", "length_km", "diameter_m", "k_mm", "loss_coefficient", 
            "in_service", "hydrant_in_junction", "hydrant_out_junction", "hydrant_pipe", "hydrant_sink"]
    vals = [name, length_km, diameter_m, k_mm, loss_coefficient, False, junction, 0, 0, 0]
    _set_entries(net, "hydrant", index, **dict(zip(cols, vals)), **kwargs)
    return index

def create_hydrants(net, junctions, name = None, index = None, length_km = 0.001, diameter_m = 0.08, k_mm = 0.1, loss_coefficient = 0, **kwargs):
    '''
    Adds multiple hydrants into table net["hydrant"]. At first it is not in service but has to be activated using insert_hydrant_into_grid(net, hydrant).

    :param net: The pandapipes network in which the element should be created
    :type net: pandapipesNet
    :param junction: The indices of the junction to which the hydrant is connected.
    :type junction: array_like
    :param name: The name for this hydrant
    :type name: string, default None
    :param index: Force a specified ID if it is available. If None, the index one higher than the\
            highest already existing index is selected.
    :param length_km: The length of this hydrant, i.e. the hydrant pipe in kilometers.
    :type length_km: float, default 0.001
    :param diameter_m: The diameter for this hydrant, i.e. the hydrant pipe in meters.
    :type diameter_m: string, default 0.08
    :param k_mm: The roughness for this hydrant, i.e. the hydrant pipe in milimeters.
    :type k_mm: float, default 0.1
    :param loss_coefficient: The additional loss coefficient for this hydrant, this could represent for example an additional firehose etc.
    :type loss_coefficient: float, default 0
    :param kwargs: Additional keyword arguments will be added as further columns to the\
            net["hydrant"] table
    :type kwargs: dict
    :return: index - The unique ID of the created element
    :rtype: int
    '''
    add_new_component(net, Hydrant)

    _check_multiple_junction_elements(net, junctions)
    index = _get_multiple_index_with_check(net, "hydrant", index, len(junctions))

    entries = {"name": name, "length_km": length_km, "diameter_m": diameter_m, "k_mm": k_mm, "loss_coefficient": loss_coefficient,
               "in_service": False, "hydrant_in_junction": junctions, "hydrant_out_junction": 0, "hydrant_pipe": 0, "hydrant_sink": 0}
    _set_multiple_entries(net, "hydrant", index, **entries, **kwargs)

def delete_hydrant(net, hydrant):
    '''
    Deletes the hydrant from table net["hydrant"].

    :param net: The pandapipes network
    :type net: pandapipesNet
    :param hydrant: The index of the hydrant
    :type hydrant: int
    '''
    _check_hydrant(net,hydrant)
    net.hydrant.drop(hydrant, inplace = True)


def insert_hydrant_into_net(net, hydrant):
    '''
    The hydrant gets inserted into the net. 
    For that an additional pipe (the hydrant pipe) and a junction with a sink representing the hydrant as a whole is added to the net. 
    The indices of those components are saved in the net["hydrant"] table.

    :param net: The pandapipes network in which the element is created
    :type net: pandapipesNet
    :param hydrant: The index of the hydrant in the table.
    :type hydrant: int
    '''

    _check_hydrant(net, hydrant)
    if read_from_net(net, "hydrant", hydrant, "in_service"):
        warnings.warn(f"Hydrant {hydrant} is already in service.", UserWarning)
        return

    j_in = read_from_net(net, "hydrant", hydrant, "hydrant_in_junction")

    #insert the pipe, node and sink that are also needed for the hydrant model
    j_out = create_junction(net, pn_bar= net.junction.pn_bar.loc[j_in], 
                                        tfluid_k = net.junction.tfluid_k.loc[j_in], 
                                        height_m = net.junction.height_m.loc[j_in], 
                                        type = "hydrant_out_junction",
                                        name = f"Hydrant {hydrant} out junction")
    write_to_net(net, "hydrant", hydrant, "hydrant_out_junction", j_out)

    h_p = create_pipe_from_parameters(net, from_junction= j_in, to_junction= j_out, 
                                            length_km=read_from_net(net, "hydrant", hydrant, "length_km"), 
                                            diameter_m = read_from_net(net, "hydrant", hydrant, "diameter_m"),
                                            k_mm= read_from_net(net, "hydrant", hydrant, "k_mm"), 
                                            loss_coefficient= read_from_net(net, "hydrant", hydrant, "loss_coefficient"),
                                            name = f"Hydrant {hydrant} pipe")
    
    write_to_net(net, "hydrant", hydrant, "hydrant_pipe", h_p)

    h_s = create_sink(net, junction= j_out, mdot_kg_per_s= 0, name = f"Hydrant {hydrant} sink")      
    write_to_net(net, "hydrant", hydrant, "hydrant_sink", h_s)

    write_to_net(net, "hydrant", hydrant, "in_service", True)
    pass

def remove_hydrant_from_net(net, hydrant):
    '''
    The hydrant is removed from the net and all components that came with it (pipe, junction and sink).
    Therefore the indices of those components are deleted from the net["hydrant"] table.

    :param net: The pandapipes network
    :type net: pandapipesNet
    :param hydrant: The index of the hydrant in the table.
    :type hydrant: int
    '''

    _check_hydrant(net, hydrant)
    if not read_from_net(net, "hydrant", hydrant, "in_service"):
        #warnings.warn(f"Hydrant {hydrant} is already out of service.", UserWarning)
        return

    #remove pipe, node and sink
    j_out = read_from_net(net, "hydrant", hydrant, "hydrant_out_junction")
    h_p = read_from_net(net, "hydrant", hydrant, "hydrant_pipe")
    h_s = read_from_net(net, "hydrant", hydrant, "hydrant_sink")
    
    net.junction.drop(j_out, inplace= True)
    net.pipe.drop(h_p, inplace= True)           
    net.sink.drop(h_s, inplace = True)

    write_to_net(net, "hydrant", hydrant, "hydrant_out_junction", 0)
    write_to_net(net, "hydrant", hydrant, "hydrant_pipe", 0)
    write_to_net(net, "hydrant", hydrant, "hydrant_sink", 0)

    write_to_net(net, "hydrant", hydrant, "in_service", False)



def set_hydrant_flow(net, hydrant, mdot_kg_per_s):
    '''
    Change the flow rate of an active hydrant.

    :param net: The pandapipes network in which the element is created
    :type net: pandapipesNet
    :param hydrant: The index of the hydrant in the table.
    :type hydrant: int
    :param mdot_kg_per_s: The flow rate in kg/s.
    :type mdot_kg_per_s: float
    '''
    if read_from_net(net, "hydrant", hydrant, "in_service"):
        sink = read_from_net(net, "hydrant", hydrant, "hydrant_sink")
        write_to_net(net, "sink", sink, "mdot_kg_per_s", mdot_kg_per_s)
    else:
        raise UserWarning(f"Cannot change hydrant flow: Hydrant {hydrant} is not active.")
    
    
def _check_hydrant(net, hydrant):
    '''
    Check if the specified hydrant exists.

    :param net: The pandapipes network in which the element is created
    :type net: pandapipesNet
    :param hydrant: The index of the hydrant in the table.
    :type hydrant: int
    '''
    if hydrant not in net["hydrant"].index.values:
        raise UserWarning(f"Hydrant {hydrant} does not exist.")

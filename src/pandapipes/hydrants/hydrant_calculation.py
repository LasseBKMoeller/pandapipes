import warnings
import multiprocessing as mp
from functools import partial


import pandas as pd
from pandapipes.control.run_control import run_control
from pandapipes.hydrants.config import MODE
if MODE == "junction":
    from pandapipes.hydrants.hydrant_on_junction.hydrant_on_junction_creation import insert_hydrant_into_net, remove_hydrant_from_net
elif MODE == "pipe":
    from pandapipes.hydrants.hydrant_on_pipe.hydrant_on_pipe_creation import insert_hydrant_into_net, remove_hydrant_from_net
else: raise ImportError("You did not import the hydrants module correctly, use either import pandapipes.hydrants.hydrant_on_junction or import pandapipes.hydrants.hydrant_on_pipe")

from pandapipes.hydrants.hydrant_control import HydrantControlFlowSearch, HydrantControlFlowList

def run_hydrant_calculation(hydrant, net, hydrant_controller, **kwargs):
    '''
    Function to run a single hydrant calculation.

    :param hydrant: The index of the hydrant.
    :type hydrant: int
    :param net: The pandapipes network
    :type net: pandapipesNet
    :param hydrant_controller: The controller that should be used for the hydrant calculation
    :type hydrant_controller: Controller
    :param kwargs: Additional keyword arguments (eg. pipeflow options)
    :type kwargs: dict
    :return: the calculated results for the selected hydrant
    '''

    insert_hydrant_into_net(net, hydrant)
    hydrant_controller.set_hydrant(hydrant)

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=UserWarning)
        warnings.filterwarnings("ignore", category=FutureWarning)
        run_control(net, **kwargs)

    result = net.res_hydrant.loc[hydrant]
    #to see if the critical junction is the hydrant itself, we set it to -1
    if result["crit_junction"] == net.hydrant.hydrant_out_junction.loc[hydrant]: 
        result["crit_junction"] = -1 

    remove_hydrant_from_net(net, hydrant)
    return result


def run_full_hydrant_calculation(net, hydrant_controller, parallel = False, on_iteration = None, **kwargs):
    '''
    Run a hydrant calculation for all hydrants and collect the results.

    :param net: The pandapipes network
    :type net: pandapipesNet
    :param hydrant_controller: The controller that should be used for the hydrant calculation
    :type hydrant_controller: Controller
    :param parallel: If the calculation should be performed in parallel (takes a bit to setup, therefore not necessary for small nets)
    :type parallel: bool, default True
    :param kwargs: Additional keyword arguments
    :type kwargs: dict
    :return: The calculated results for all hydrants (eg. pipeflow options)
    :rtype: pandas.Dataframe
    '''
    #disable all hydrants
    for hydrant in net.hydrant.index:
        remove_hydrant_from_net(net, hydrant)

    if parallel == True:
        #calculate in parallel
        f = partial(run_hydrant_calculation, net = net, hydrant_controller=hydrant_controller, **kwargs)
        with mp.Pool(processes = mp.cpu_count()) as pool:
            results = pool.map(f, net.hydrant.index)
    else:
        #one by one
        results = []
        nets = []
        for hydrant in net.hydrant.index:
            run_hydrant_calculation(hydrant, net, hydrant_controller, **kwargs)
            results.append(net.res_hydrant.loc[hydrant])
            if on_iteration is not None:
                on_iteration()
    
    return pd.DataFrame(results, index=net.hydrant.index)


def run_hydrant_flow_search(net, p_min = 1.5, tol = 1e-2, parallel = False, on_iteration = None, **kwargs):
    '''
    Find the maximal flow for all hydrants given a minimal pressure.

    :param net: The pandapipes network
    :type net: pandapipesNet
    :param p_min: The minimal pressure in the grid
    :type p_min: float, default 1.5
    :param tol: The tolerance with which the pressure should be determined
    :type tol: float, default 1e-2
    :param parallel: If the calculation should be performed in parallel (takes a bit to setup, therefore not necessary for small nets). Does NOT work in QGIS!
    :type parallel: bool, default True
    :param kwargs: Additional keyword arguments (eg. pipeflow options)
    :type kwargs: dict
    :return: The calculated results for all hydrants.
    :rtype: pandas.Dataframe
    '''
    net.controller = net.controller.head(0) #delete all other controllers
    hydrant_controller = HydrantControlFlowSearch(net, hydrant = 0, p_min = p_min, tol = tol)
    results = run_full_hydrant_calculation(net, hydrant_controller, parallel= parallel, on_iteration=on_iteration, **kwargs)
    net.controller.drop(hydrant_controller.index, inplace = True)
    return results

def run_hydrant_flow_list(net, flow_list = [192, 96, 48, 24, 0], flow_unit = "m3/h", p_min = 1.5, parallel = False, on_iteration = None, **kwargs):
    '''
    Find the maximal flow for all hydrants given a list of possible flows.

    :param net: The pandapipes network
    :type net: pandapipesNet
    :param flow_list: List if flow rates that should be tested for the hydrants
    :type flow_list: arraylike, default [192, 96, 48, 24, 0]
    :param parallel: If the calculation should be performed in parallel (takes a bit to setup, therefore not necessary for small nets). Does NOT work in QGIS!
    :type parallel: bool, default True
    :param kwargs: Additional keyword arguments (eg. pipeflow options)
    :type kwargs: dict
    :return: The calculated results for all hydrants.
    :rtype: pandas.Dataframe
    '''
    net.controller = net.controller.head(0) #delete all other controllers
    hydrant_controller = HydrantControlFlowList(net, hydrant = 0, flow_list= flow_list, flow_unit = flow_unit, p_min = p_min)
    results = run_full_hydrant_calculation(net, hydrant_controller, parallel= parallel, on_iteration=on_iteration, **kwargs)
    net.controller.drop(hydrant_controller.index, inplace = True)
    return results


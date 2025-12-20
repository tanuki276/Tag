import sys
import yaml
import os
from pathlib import Path
import numpy as np
import random
import heapq
import copy
from enum import Enum, IntEnum
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional, Tuple, Protocol, runtime_checkable
from collections import defaultdict

class ActionType(str, Enum):
    MOVE = "MOVE"
    SKILL = "SKILL"
    WAIT = "WAIT"
    INTERACT = "INTERACT"

class Priority(IntEnum):
    SYSTEM = 100
    SKILL_HIGH = 80
    SKILL_MID = 50
    MOVE_DEFAULT = 30
    WAIT = 0

class ActorStatus(BaseModel):
    a_id: str
    pos: Optional[Tuple[int, int]]
    is_oni: bool
    alive: bool
    escaped: bool

class Element(BaseModel):
    pos: Tuple[int, int]
    kind: str
    properties: Dict[str, Any] = Field(default_factory=dict)

class Memory(BaseModel):
    short_term: Dict[str, Any] = Field(default_factory=dict)
    long_term: Dict[str, Any] = Field(default_factory=dict)
    predictions: Dict[str, Tuple[int, int]] = Field(default_factory=dict)

class LocalView(BaseModel):
    pos: Tuple[int, int]
    actors: List[ActorStatus] = Field(default_factory=list)
    elements: List[Element] = Field(default_factory=list)
    memory: Memory = Field(default_factory=Memory)

class Intent(BaseModel):
    target_pos: Tuple[int, int]
    priority: int = Priority.MOVE_DEFAULT
    action_type: ActionType = ActionType.MOVE
    metadata: Dict[str, Any] = Field(default_factory=dict)

class Action(BaseModel):
    target_pos: Optional[Tuple[int, int]]
    status_update: Dict[str, Any] = Field(default_factory=dict)

@runtime_checkable
class IGrid(Protocol):
    def is_walkable(self, pos: Tuple[int, int]) -> bool: ...
    def in_bounds(self, pos: Tuple[int, int]) -> bool: ...
    @property
    def shape(self) -> Tuple[int, int]: ...

@runtime_checkable
class IActor(Protocol):
    a_id: str
    pos: Optional[Tuple[int, int]]
    is_oni: bool
    alive: bool
    escaped: bool
    def decide(self, view: LocalView) -> Intent: ...
    def get_public_status(self) -> ActorStatus: ...
    def commit_status(self, target_pos: Optional[Tuple[int, int]], status_update: Dict[str, Any]) -> None: ...
    def tick(self) -> None: ...
    def clone(self) -> 'IActor': ...

class Pathfinder:
    def __init__(self, grid: IGrid):
        self.grid = grid

    def _dist(self, a: Tuple[int, int], b: Tuple[int, int]) -> float:
        dx, dy = abs(a[0]-b[0]), abs(a[1]-b[1])
        return dx + dy + (1.414-2.0)*min(dx, dy)

    def find_path(self, start: Tuple[int, int], goal: Tuple[int, int]) -> List[Tuple[int, int]]:
        if not self.grid.in_bounds(goal) or not self.grid.is_walkable(goal):
            return [start]
        oheap = [(0, start)]
        came_from, g_score = {}, {start: 0}
        close_set = set()
        while oheap:
            _, curr = heapq.heappop(oheap)
            if curr == goal:
                path = []
                while curr in came_from:
                    path.append(curr)
                    curr = came_from[curr]
                return [start]+path[::-1]
            close_set.add(curr)
            for di,dj in [(0,1),(0,-1),(1,0),(-1,0),(1,1),(1,-1),(-1,1),(-1,-1)]:
                ni,nj=curr[0]+di,curr[1]+dj
                neighbor=(ni,nj)
                if not self.grid.in_bounds(neighbor) or not self.grid.is_walkable(neighbor) or neighbor in close_set:
                    continue
                if di!=0 and dj!=0:
                    if not self.grid.is_walkable((curr[0]+di,curr[1])) or not self.grid.is_walkable((curr[0],curr[1]+dj)):
                        continue
                tg=g_score[curr]+(1.414 if di!=0 and dj!=0 else 1.0)
                if tg<g_score.get(neighbor,float('inf')):
                    came_from[neighbor],g_score[neighbor]=curr,tg
                    heapq.heappush(oheap,(tg+self._dist(neighbor,goal),neighbor))
        return [start]

class CombatResolver:
    @staticmethod
    def resolve(final_pos: Dict[str, Tuple[int,int]], actors: Dict[str, IActor]) -> Dict[str, Dict[str, Any]]:
        updates=defaultdict(dict)
        onis=[a_id for a_id,a in actors.items() if a.is_oni]
        humans=[a_id for a_id,a in actors.items() if not a.is_oni and a.alive]
        for o_id in onis:
            for h_id in humans:
                if final_pos.get(o_id)==final_pos.get(h_id):
                    updates[h_id]['alive']=False
        return updates

class ActionResolver:
    def resolve(self,intents: Dict[str, Intent], state: 'WorldState') -> Dict[str, Action]:
        pf=Pathfinder(state.grid)
        sorted_ids=sorted(intents.keys(),key=lambda x:(intents[x].priority,state.actor_data[x].is_oni),reverse=True)
        final_pos,reserved={},set()
        for a_id in sorted_ids:
            actor=state.actor_data[a_id]
            if not actor.pos: continue
            path=pf.find_path(actor.pos,intents[a_id].target_pos)[:2]
            step=path[-1] if len(path)>1 and path[-1] not in reserved else actor.pos
            final_pos[a_id]=step
            reserved.add(step)
        combat_updates=CombatResolver.resolve(final_pos,state.actor_data)
        return {a_id: Action(target_pos=final_pos.get(a_id),status_update=combat_updates[a_id]) for a_id in intents}

class WorldRule:
    @staticmethod
    def check_termination(state: 'WorldState') -> Tuple[bool, Optional[str]]:
        humans=[h for h in state.actor_data.values() if not h.is_oni]
        alive_humans=[h for h in humans if h.alive and not h.escaped]
        if not alive_humans:
            esc=len([h for h in humans if h.escaped])
            return True,("PERFECT" if esc==len(humans) else "PARTIAL" if esc>0 else "ANNIHILATED")
        if state.turn>=state.max_turns:
            return True,"TIMEOUT"
        return False,None

class WorldState:
    def __init__(self, grid: IGrid, actors: Dict[str, IActor], elements: Dict[Tuple[int,int],Element], exit_pos: Tuple[int,int], max_turns:int, turn:int=0, exit_open:bool=False):
        self.grid,self.actor_data,self.map_elements=grid,actors,elements
        self.exit_pos,self.max_turns,self.turn,self.exit_open=exit_pos,max_turns,turn,exit_open

    def apply(self,actions: Dict[str,Action]) -> 'WorldState':
        new_actors={a_id:a.clone() for a_id,a in self.actor_data.items()}
        for a_id,actor in new_actors.items():
            if a_id in actions:
                actor.commit_status(actions[a_id].target_pos,actions[a_id].status_update)
            actor.tick()
        for a in new_actors.values():
            if not a.is_oni and a.alive and a.pos==self.exit_pos and self.exit_open:
                a.commit_status(None,{"escaped":True})
        new_state=WorldState(self.grid,new_actors,self.map_elements,self.exit_pos,self.max_turns,self.turn+1,self.exit_open)
        is_term,reason=WorldRule.check_termination(new_state)
        new_state.is_terminal,new_state.termination_reason=is_term,reason
        return new_state

class WorldGenerator:
    def __init__(self, seed=None):
        self.seed=seed
        if seed is not None:
            random.seed(seed)
    def build_initial_state(self, config):
        from pkg.engine.grid import Grid
        from pkg.engine.actor import Actor
        grid=Grid(config["world"]["width"],config["world"]["height"])
        actors={}
        for a_cfg in config["actors"]:
            actors[a_cfg["id"]]=Actor(**a_cfg)
        elements={}
        exit_pos=tuple(config["world"]["exit_pos"])
        max_turns=config["world"]["max_turns"]
        return WorldState(grid,actors,elements,exit_pos,max_turns)

def load_config(config_path: str) -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def main():
    try:
        config=load_config("config/settings/global_constants.yaml")
        learning_cfg=load_config("config/settings/learning.yaml")
    except FileNotFoundError:
        sys.exit(1)
    from pkg.utils.logger import GameLogger
    from pkg.utils.visualizer import MapVisualizer
    from pkg.engine.core import SimulationCore
    from pkg.analysis.evaluator import SimulationEvaluator
    logger=GameLogger(level="INFO")
    grid_size=(config["world"]["width"],config["world"]["height"])
    viz=MapVisualizer(size=grid_size)
    generator=WorldGenerator(seed=config.get("seed"))
    world_state=generator.build_initial_state(config)
    core=SimulationCore(state=world_state,config=config,learning_cfg=learning_cfg)
    evaluator=SimulationEvaluator()
    viz.save_frame(0,core.get_snapshot())
    try:
        for turn in range(1,config["world"]["max_turns"]+1):
            step_result=core.step()
            evaluator.record_step(step_result)
            logger.log_turn(turn,step_result)
            viz.save_frame(turn,step_result.snapshot)
            if step_result.is_terminal:
                break
    except Exception as e:
        logger.error(f"Engine Crash: {str(e)}")
        raise
    report=evaluator.generate_final_report()
    logger.print_report(report)

if __name__=="__main__":
    main()
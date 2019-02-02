import sc2
from sc2 import run_game, maps, Race, Difficulty, position, Result
from sc2.player import Bot, Computer
from sc2.constants import *
import random
import cv2
import numpy as np
import time

class TBot(sc2.BotAI):
	def __init__(self):
		self.ITERATIONS_PER_MINUTE = 165
		self.MAXWORKERS = 70

	async def on_step(self, iteration):
		self.iteration = iteration
		await self.distribute_workers()
		await self.build_workers()
		await self.build_ramp_wall()
		await self.build_refineries()
		await self.build_offensive_buildings()
		await self.build_supply_depots()
		await self.expand()
		await self.build_offense()
		await self.attack()

	async def build_workers(self):
		if (len(self.units(COMMANDCENTER)) * 16) > len(self.units(SCV)) and len(self.units(SCV)) < self.MAXWORKERS:
			for nexus in self.units(COMMANDCENTER).ready.noqueue:
				if self.can_afford(SCV) and not self.already_pending(SCV):
					await self.do(nexus.train(SCV))

	async def build_ramp_wall(self):
		if self.units(SUPPLYDEPOT).amount <= 2:
			for depo in self.units(SUPPLYDEPOT).ready:
				for unit in self.known_enemy_units.not_structure:
					if unit.position.to2.distance_to(depo.position.to2) < 15:
						break
				else:
					await self.do(depo(MORPH_SUPPLYDEPOT_LOWER))

			for depo in self.units(SUPPLYDEPOT).ready:
				for unit in self.known_enemy_units.not_structure:
					if unit.position.to2.distance_to(depo.position.to2) < 10:
						await self.do(depo(MORPH_SUPPLYDEPOT_RAISE))
						break

			depot_placement_positions = self.main_base_ramp.corner_depots

			barracks_placement_position = None
			barracks_placement_position = self.main_base_ramp.barracks_correct_placement

			depots = self.units(SUPPLYDEPOT) | self.units(SUPPLYDEPOTLOWERED)

			if depots:
				depot_placement_positions = {d for d in depot_placement_positions if depots.closest_distance_to(d) > 1}

			if self.can_afford(SUPPLYDEPOT) and not self.already_pending(SUPPLYDEPOT):
				if len(depot_placement_positions) == 0:
					return

				target_depot_location = depot_placement_positions.pop()
				ws = self.workers.gathering
				if ws:
					worker = ws.random
					await self.do(worker.build(SUPPLYDEPOT, target_depot_location))

			if depots.ready.exists and self.can_afford(BARRACKS) and not self.already_pending(BARRACKS):
				if self.units(BARRACKS).amount + self.already_pending(BARRACKS) > 0:
					return
				ws = self.workers.gathering
				if ws and barracks_placement_position:
					worker = ws.random
					await self.do(worker.build(BARRACKS, barracks_placement_position))

	async def expand(self):
		if (len(self.units(COMMANDCENTER)) * 16) < self.MAXWORKERS:
			if self.units(COMMANDCENTER).amount < (self.iteration / self.ITERATIONS_PER_MINUTE) and self.can_afford(COMMANDCENTER):
				await self.expand_now()

	async def build_offensive_buildings(self):
		cc = random.choice(self.units(COMMANDCENTER).ready)
		if self.units(BARRACKS).ready.exists and not self.units(FACTORY):
			if self.can_afford(FACTORY) and not self.already_pending(FACTORY):
				await self.build(FACTORY, near=cc)
		if len(self.units(BARRACKS)) < 5:
			if self.can_afford(BARRACKS) and not self.already_pending(BARRACKS):
				await self.build(BARRACKS, near=cc)


	async def build_supply_depots(self):
		if self.supply_left < 3:
			if self.can_afford(SUPPLYDEPOT) and self.already_pending(SUPPLYDEPOT) < 2:
				cc = self.units(COMMANDCENTER).random
				await self.build(SUPPLYDEPOT, near=cc.position.towards(self.game_info.map_center,8))


	async def build_refineries(self):
		for cc in self.units(COMMANDCENTER).ready:
			ref = self.state.vespene_geyser.closer_than(15.0, cc)
			for r in ref:
				if not self.can_afford(REFINERY):
					break
				worker = self.select_build_worker(r.position)
				if worker is None:
					break
				if not self.units(REFINERY).closer_than(1.0, r).exists:
					await self.do(worker.build(REFINERY, r))

	async def build_offense(self):
		if len(self.units(MARINE)) < 40:
			for b in self.units(BARRACKS).noqueue:
				await self.do(b.train(MARINE))

	async def attack(self):
		if len(self.units(MARINE)) > 20:
			for unit in self.units(MARINE).idle:
				await self.do(unit.attack(self.enemy_start_locations[0]))
		elif len(self.known_enemy_units) > 0:
			for unit in self.units(MARINE).idle:
				await self.do(unit.attack(random.choice(self.known_enemy_units)))


run_game(maps.get("AbyssalReefLE"), [
	Bot(Race.Terran, TBot()),
	Computer(Race.Protoss, Difficulty.Easy)
	], realtime=False)
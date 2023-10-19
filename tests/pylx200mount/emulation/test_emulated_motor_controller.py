import asyncio
import contextlib
import logging
import typing
import unittest.mock
from dataclasses import dataclass
from datetime import datetime
from unittest import IsolatedAsyncioTestCase

import astropy.units as u
import pylx200mount
from astropy.coordinates import Angle


@dataclass
class ExpectedData:
    time: float
    position: int
    velocity: int


class TestEmulatedMotorController(IsolatedAsyncioTestCase):
    @contextlib.asynccontextmanager
    async def create_emulated_motor(self) -> typing.AsyncGenerator[None, None]:
        log = logging.getLogger(type(self).__name__)
        self.conversion_factor = Angle(0.0001 * u.deg)
        with unittest.mock.patch(
            "pylx200mount.emulation.emulated_motor_controller.get_time", self.get_time
        ):
            async with pylx200mount.emulation.EmulatedMotorController(
                initial_position=Angle(0.0, u.deg),
                log=log,
                conversion_factor=self.conversion_factor,
                hub_port=0,
            ) as self.emulated_motor_controller:
                yield

    async def test_init_emulated_motor(self) -> None:
        log = logging.getLogger(type(self).__name__)
        conversion_factor = Angle(0.0001 * u.deg)
        emulated_motor_controller = pylx200mount.emulation.EmulatedMotorController(
            initial_position=Angle(0.0, u.deg),
            log=log,
            conversion_factor=conversion_factor,
            hub_port=0,
        )
        assert emulated_motor_controller.is_alt
        assert not emulated_motor_controller.attached

        await emulated_motor_controller.connect()
        assert emulated_motor_controller.attached

        await emulated_motor_controller.disconnect()
        assert not emulated_motor_controller.attached

    def get_time(self) -> float:
        return self.t

    async def assert_position_and_velocity(self, expected_data: ExpectedData) -> None:
        self.t = expected_data.time
        await asyncio.sleep(0.1)
        assert (
            self.emulated_motor_controller.position
            == expected_data.position
            * self.emulated_motor_controller._conversion_factor
        )
        assert (
            self.emulated_motor_controller.velocity
            == expected_data.velocity
            * self.emulated_motor_controller._conversion_factor
        )

    async def test_move_far_positive(self) -> None:
        async with self.create_emulated_motor():
            command_time = self.t = datetime.now().astimezone().timestamp()
            await self.emulated_motor_controller.move(
                target_position=1000000 * self.conversion_factor
            )
            for expected_data in [
                ExpectedData(command_time + 1.0, 25000, 50000),
                ExpectedData(command_time + 2.0, 100000, 100000),
                ExpectedData(command_time + 3.0, 200000, 100000),
                ExpectedData(command_time + 10.0, 900000, 100000),
                ExpectedData(command_time + 11.0, 975000, 50000),
                ExpectedData(command_time + 12.0, 1000000, 0),
            ]:
                await self.assert_position_and_velocity(expected_data)

    async def test_move_far_positive_from_position(self) -> None:
        async with self.create_emulated_motor():
            self.emulated_motor_controller.position = Angle(45.0, u.deg)
            command_time = self.t = datetime.now().astimezone().timestamp()
            await self.emulated_motor_controller.move(
                target_position=1000000 * self.conversion_factor
            )
            for expected_data in [
                ExpectedData(command_time + 1.0, 475000, 50000),
                ExpectedData(command_time + 2.0, 550000, 100000),
                ExpectedData(command_time + 3.0, 650000, 100000),
                ExpectedData(command_time + 6.0, 943750, 75000),
                ExpectedData(command_time + 7.0, 993750, 25000),
                ExpectedData(command_time + 8.0, 1000000, 0),
            ]:
                await self.assert_position_and_velocity(expected_data)

    async def test_move_far_positive_to_same_position(self) -> None:
        async with self.create_emulated_motor():
            self.emulated_motor_controller.position = Angle(45.0, u.deg)
            command_time = self.t = datetime.now().astimezone().timestamp()
            await self.emulated_motor_controller.move(
                target_position=1000000 * self.conversion_factor
            )
            for expected_data in [
                ExpectedData(command_time + 1.0, 475000, 50000),
                ExpectedData(command_time + 2.0, 550000, 100000),
                ExpectedData(command_time + 3.0, 650000, 100000),
            ]:
                await self.assert_position_and_velocity(expected_data)
            await self.emulated_motor_controller.move(
                target_position=1000000 * self.conversion_factor
            )
            for expected_data in [
                ExpectedData(command_time + 3.1, 660000, 100000),
                ExpectedData(command_time + 6.0, 943750, 75000),
                ExpectedData(command_time + 7.0, 993750, 25000),
                ExpectedData(command_time + 8.0, 1000000, 0),
            ]:
                await self.assert_position_and_velocity(expected_data)

    async def test_move_far_positive_to_different_position(self) -> None:
        async with self.create_emulated_motor():
            command_time = self.t = datetime.now().astimezone().timestamp()
            await self.emulated_motor_controller.move(
                target_position=1000000 * self.conversion_factor
            )
            for expected_data in [
                ExpectedData(command_time + 1.0, 25000, 50000),
                ExpectedData(command_time + 2.0, 100000, 100000),
                ExpectedData(command_time + 3.0, 200000, 100000),
            ]:
                await self.assert_position_and_velocity(expected_data)
            await self.emulated_motor_controller.move(
                target_position=100000 * self.conversion_factor
            )
            for expected_data in [
                ExpectedData(command_time + 3.1, 209750, 95000),
                ExpectedData(command_time + 4.0, 275000, 50000),
                ExpectedData(command_time + 5.0, 300000, 0),
                ExpectedData(command_time + 6.0, 275000, -50000),
                ExpectedData(command_time + 7.0, 200000, -100000),
                ExpectedData(command_time + 8.0, 125000, -50000),
                ExpectedData(command_time + 9.0, 100000, 0),
            ]:
                await self.assert_position_and_velocity(expected_data)

    async def test_move_far_positive_to_different_position_from_pos(self) -> None:
        async with self.create_emulated_motor():
            self.emulated_motor_controller.position = Angle(45.0, u.deg)
            command_time = self.t = datetime.now().astimezone().timestamp()
            await self.emulated_motor_controller.move(
                target_position=1045000 * self.conversion_factor
            )
            for expected_data in [
                ExpectedData(command_time + 1.0, 475000, 50000),
                ExpectedData(command_time + 2.0, 550000, 100000),
                ExpectedData(command_time + 3.0, 650000, 100000),
            ]:
                await self.assert_position_and_velocity(expected_data)
            await self.emulated_motor_controller.move(
                target_position=145000 * self.conversion_factor
            )
            for expected_data in [
                ExpectedData(command_time + 3.1, 659750, 95000),
                ExpectedData(command_time + 4.0, 725000, 50000),
                ExpectedData(command_time + 5.0, 750000, 0),
                ExpectedData(command_time + 6.0, 725000, -50000),
                ExpectedData(command_time + 7.0, 650000, -100000),
                ExpectedData(command_time + 11.0, 250000, -100000),
                ExpectedData(command_time + 12.0, 172563, -52500),
                ExpectedData(command_time + 13.0, 145062, -2500),
                ExpectedData(command_time + 13.5, 145000, 0),
            ]:
                await self.assert_position_and_velocity(expected_data)

    async def test_move_far_positive_to_different_position_from_neg(self) -> None:
        async with self.create_emulated_motor():
            self.emulated_motor_controller.position = Angle(-50.0, u.deg)
            command_time = self.t = datetime.now().astimezone().timestamp()
            await self.emulated_motor_controller.move(
                target_position=50000 * self.conversion_factor
            )
            for expected_data in [
                ExpectedData(command_time + 1.0, -475000, 50000),
                ExpectedData(command_time + 2.0, -400000, 100000),
                ExpectedData(command_time + 3.0, -300000, 100000),
                ExpectedData(command_time + 4.0, -200000, 100000),
            ]:
                await self.assert_position_and_velocity(expected_data)
            await self.emulated_motor_controller.move(
                target_position=-250000 * self.conversion_factor
            )
            for expected_data in [
                ExpectedData(command_time + 4.1, -190250, 95000),
                ExpectedData(command_time + 5.0, -125000, 50000),
                ExpectedData(command_time + 6.0, -100000, 0),
                ExpectedData(command_time + 7.0, -125000, -50000),
                ExpectedData(command_time + 8.0, -196410, -73205),
                ExpectedData(command_time + 9.0, -244615, -23205),
                ExpectedData(command_time + 10.0, -250000, 0),
            ]:
                await self.assert_position_and_velocity(expected_data)

    async def test_move_far_positive_in_two_steps(self) -> None:
        async with self.create_emulated_motor():
            command_time = self.t = datetime.now().astimezone().timestamp()
            await self.emulated_motor_controller.move(
                target_position=1000000 * self.conversion_factor
            )
            for expected_data in [
                ExpectedData(command_time + 1.0, 25000, 50000),
                ExpectedData(command_time + 2.0, 100000, 100000),
                ExpectedData(command_time + 10.0, 900000, 100000),
                ExpectedData(command_time + 11.0, 975000, 50000),
                ExpectedData(command_time + 12.0, 1000000, 0),
            ]:
                await self.assert_position_and_velocity(expected_data)
            await self.emulated_motor_controller.move(
                target_position=2000000 * self.conversion_factor
            )
            for expected_data in [
                ExpectedData(command_time + 13.0, 1025000, 50000),
                ExpectedData(command_time + 14.0, 1100000, 100000),
                # Angle wrap!!!
                ExpectedData(command_time + 22.0, -1700000, 100000),
                ExpectedData(command_time + 23.0, -1625000, 50000),
                ExpectedData(command_time + 24.0, -1600000, 0),
            ]:
                await self.assert_position_and_velocity(expected_data)

    async def test_move_near_positive(self) -> None:
        async with self.create_emulated_motor():
            command_time = self.t = datetime.now().astimezone().timestamp()
            await self.emulated_motor_controller.move(
                target_position=100000 * self.conversion_factor
            )
            for expected_data in [
                ExpectedData(command_time + 0.5, 6250, 25000),
                ExpectedData(command_time + 1.0, 25000, 50000),
                ExpectedData(command_time + 1.5, 55882, 66421),
                ExpectedData(command_time + 2.0, 82843, 41421),
                ExpectedData(command_time + 2.5, 97303, 16421),
                ExpectedData(command_time + 2.9, 100000, 0),
            ]:
                await self.assert_position_and_velocity(expected_data)

    async def test_move_near_positive_and_back(self) -> None:
        async with self.create_emulated_motor():
            command_time = self.t = datetime.now().astimezone().timestamp()
            await self.emulated_motor_controller.move(
                target_position=100000 * self.conversion_factor
            )
            for expected_data in [
                ExpectedData(command_time + 0.5, 6250, 25000),
                ExpectedData(command_time + 1.0, 25000, 50000),
                ExpectedData(command_time + 1.5, 55882, 66421),
                ExpectedData(command_time + 2.0, 82843, 41421),
                ExpectedData(command_time + 2.5, 97303, 16421),
                ExpectedData(command_time + 3.0, 100000, 0),
            ]:
                await self.assert_position_and_velocity(expected_data)
            await self.emulated_motor_controller.move(
                target_position=0 * self.conversion_factor
            )
            for expected_data in [
                ExpectedData(command_time + 3.5, 93750, -25000),
                ExpectedData(command_time + 4.0, 75000, -50000),
                ExpectedData(command_time + 4.5, 44118, -66421),
                ExpectedData(command_time + 5.0, 17157, -41421),
                ExpectedData(command_time + 5.5, 2697, -16421),
                ExpectedData(command_time + 6.0, 0, 0),
            ]:
                await self.assert_position_and_velocity(expected_data)

    async def test_move_far_negative(self) -> None:
        async with self.create_emulated_motor():
            command_time = self.t = datetime.now().astimezone().timestamp()
            await self.emulated_motor_controller.move(
                target_position=-1000000 * self.conversion_factor,
            )
            for expected_data in [
                ExpectedData(command_time + 1.0, -25000, -50000),
                ExpectedData(command_time + 2.0, -100000, -100000),
                ExpectedData(command_time + 3.0, -200000, -100000),
                ExpectedData(command_time + 10.0, -900000, -100000),
                ExpectedData(command_time + 11.0, -975000, -50000),
                ExpectedData(command_time + 12.0, -1000000, 0),
            ]:
                await self.assert_position_and_velocity(expected_data)

    async def test_move_far_negative_from_position(self) -> None:
        async with self.create_emulated_motor():
            self.emulated_motor_controller.position = Angle(45.0, u.deg)
            command_time = self.t = datetime.now().astimezone().timestamp()
            await self.emulated_motor_controller.move(
                target_position=-1000000 * self.conversion_factor,
            )
            for expected_data in [
                ExpectedData(command_time + 1.0, 425000, -50000),
                ExpectedData(command_time + 2.0, 350000, -100000),
                ExpectedData(command_time + 3.0, 250000, -100000),
                ExpectedData(command_time + 10.0, -450000, -100000),
                ExpectedData(command_time + 11.0, -550000, -100000),
                ExpectedData(command_time + 12.5, -700000, -100000),
                ExpectedData(command_time + 15.0, -943750, -75000),
                ExpectedData(command_time + 16.0, -993750, -25000),
                ExpectedData(command_time + 16.5, -1000000, 0),
            ]:
                await self.assert_position_and_velocity(expected_data)

    async def test_move_far_negative_to_same_position(self) -> None:
        async with self.create_emulated_motor():
            self.emulated_motor_controller.position = Angle(45.0, u.deg)
            command_time = self.t = datetime.now().astimezone().timestamp()
            await self.emulated_motor_controller.move(
                target_position=-1000000 * self.conversion_factor,
            )
            for expected_data in [
                ExpectedData(command_time + 1.0, 425000, -50000),
                ExpectedData(command_time + 2.0, 350000, -100000),
                ExpectedData(command_time + 3.0, 250000, -100000),
            ]:
                await self.assert_position_and_velocity(expected_data)
            await self.emulated_motor_controller.move(
                target_position=-1000000 * self.conversion_factor,
            )
            for expected_data in [
                ExpectedData(command_time + 3.1, 240000, -100000),
                ExpectedData(command_time + 10.0, -450000, -100000),
                ExpectedData(command_time + 11.0, -550000, -100000),
                ExpectedData(command_time + 12.5, -700000, -100000),
                ExpectedData(command_time + 15.0, -943750, -75000),
                ExpectedData(command_time + 16.0, -993750, -25000),
                ExpectedData(command_time + 16.5, -1000000, 0),
            ]:
                await self.assert_position_and_velocity(expected_data)

    async def test_move_far_negative_to_different_position(self) -> None:
        async with self.create_emulated_motor():
            command_time = self.t = datetime.now().astimezone().timestamp()
            await self.emulated_motor_controller.move(
                target_position=-1000000 * self.conversion_factor,
            )
            for expected_data in [
                ExpectedData(command_time + 1.0, -25000, -50000),
                ExpectedData(command_time + 2.0, -100000, -100000),
                ExpectedData(command_time + 3.0, -200000, -100000),
            ]:
                await self.assert_position_and_velocity(expected_data)
            await self.emulated_motor_controller.move(
                target_position=-100000 * self.conversion_factor,
            )
            for expected_data in [
                ExpectedData(command_time + 3.1, -209750, -95000),
                ExpectedData(command_time + 4.0, -275000, -50000),
                ExpectedData(command_time + 5.0, -300000, 0),
                ExpectedData(command_time + 6.0, -275000, 50000),
                ExpectedData(command_time + 7.0, -200000, 100000),
                ExpectedData(command_time + 8.0, -125000, 50000),
                ExpectedData(command_time + 9.0, -100000, 0),
            ]:
                await self.assert_position_and_velocity(expected_data)

    async def test_move_far_negative_to_different_position_from_pos(self) -> None:
        async with self.create_emulated_motor():
            command_time = self.t = datetime.now().astimezone().timestamp()
            self.emulated_motor_controller.position = Angle(45.0, u.deg)
            await self.emulated_motor_controller.move(
                target_position=-955000 * self.conversion_factor,
            )
            for expected_data in [
                ExpectedData(command_time + 1.0, 425000, -50000),
                ExpectedData(command_time + 2.0, 350000, -100000),
                ExpectedData(command_time + 3.0, 250000, -100000),
            ]:
                await self.assert_position_and_velocity(expected_data)
            await self.emulated_motor_controller.move(
                target_position=550000 * self.conversion_factor,
            )
            for expected_data in [
                ExpectedData(command_time + 3.1, 240250, -95000),
                ExpectedData(command_time + 4.0, 175000, -50000),
                ExpectedData(command_time + 5.0, 150000, 0),
                ExpectedData(command_time + 6.0, 175000, 50000),
                ExpectedData(command_time + 7.0, 250000, 100000),
                ExpectedData(command_time + 8.0, 350000, 100000),
                ExpectedData(command_time + 9.0, 450000, 100000),
                ExpectedData(command_time + 10.0, 525000, 50000),
                ExpectedData(command_time + 11.0, 550000, 0),
            ]:
                await self.assert_position_and_velocity(expected_data)

    async def test_move_far_negative_to_different_position_from_neg(self) -> None:
        async with self.create_emulated_motor():
            self.emulated_motor_controller.position = Angle(-50.0, u.deg)
            command_time = self.t = datetime.now().astimezone().timestamp()
            await self.emulated_motor_controller.move(
                target_position=-1050000 * self.conversion_factor,
            )
            for expected_data in [
                ExpectedData(command_time + 1.0, -525000, -50000),
                ExpectedData(command_time + 2.0, -600000, -100000),
                ExpectedData(command_time + 3.0, -700000, -100000),
            ]:
                await self.assert_position_and_velocity(expected_data)
            await self.emulated_motor_controller.move(
                target_position=-150000 * self.conversion_factor,
            )
            for expected_data in [
                ExpectedData(command_time + 3.1, -709750, -95000),
                ExpectedData(command_time + 4.0, -775000, -50000),
                ExpectedData(command_time + 5.0, -800000, 0),
                ExpectedData(command_time + 6.0, -775000, 50000),
                ExpectedData(command_time + 7.0, -700000, 100000),
                ExpectedData(command_time + 9.0, -500000, 100000),
                ExpectedData(command_time + 11.0, -300000, 100000),
                ExpectedData(command_time + 12.0, -206250, 75000),
                ExpectedData(command_time + 13.0, -156250, 25000),
                ExpectedData(command_time + 13.5, -150000, 0),
            ]:
                await self.assert_position_and_velocity(expected_data)

    async def test_move_far_negative_in_two_steps(self) -> None:
        async with self.create_emulated_motor():
            command_time = self.t = datetime.now().astimezone().timestamp()
            await self.emulated_motor_controller.move(
                target_position=-1000000 * self.conversion_factor
            )
            for expected_data in [
                ExpectedData(command_time + 1.0, -25000, -50000),
                ExpectedData(command_time + 2.0, -100000, -100000),
                ExpectedData(command_time + 10.0, -900000, -100000),
                ExpectedData(command_time + 11.0, -975000, -50000),
                ExpectedData(command_time + 12.0, -1000000, 0),
            ]:
                await self.assert_position_and_velocity(expected_data)
            await self.emulated_motor_controller.move(
                target_position=-2000000 * self.conversion_factor
            )
            for expected_data in [
                ExpectedData(command_time + 13.0, -1025000, -50000),
                ExpectedData(command_time + 14.0, -1100000, -100000),
                ExpectedData(command_time + 22.0, 1700000, -100000),
                ExpectedData(command_time + 23.0, 1625000, -50000),
                ExpectedData(command_time + 24.0, 1600000, 0),
            ]:
                await self.assert_position_and_velocity(expected_data)

    async def test_move_near_negative(self) -> None:
        async with self.create_emulated_motor():
            command_time = self.t = datetime.now().astimezone().timestamp()
            await self.emulated_motor_controller.move(
                target_position=-100000 * self.conversion_factor
            )
            for expected_data in [
                ExpectedData(command_time + 0.5, -6250, -25000),
                ExpectedData(command_time + 1.0, -25000, -50000),
                ExpectedData(command_time + 1.5, -55882, -66421),
                ExpectedData(command_time + 2.0, -82843, -41421),
                ExpectedData(command_time + 2.5, -97303, -16421),
                ExpectedData(command_time + 3.0, -100000, 0),
            ]:
                await self.assert_position_and_velocity(expected_data)

    async def test_move_near_negative_and_back(self) -> None:
        async with self.create_emulated_motor():
            command_time = self.t = datetime.now().astimezone().timestamp()
            await self.emulated_motor_controller.move(
                target_position=-100000 * self.conversion_factor
            )
            for expected_data in [
                ExpectedData(command_time + 0.5, -6250, -25000),
                ExpectedData(command_time + 1.0, -25000, -50000),
                ExpectedData(command_time + 1.5, -55882, -66421),
                ExpectedData(command_time + 2.0, -82843, -41421),
                ExpectedData(command_time + 2.5, -97303, -16421),
                ExpectedData(command_time + 3.0, -100000, 0),
            ]:
                await self.assert_position_and_velocity(expected_data)
            await self.emulated_motor_controller.move(
                target_position=0 * self.conversion_factor
            )
            for expected_data in [
                ExpectedData(command_time + 3.5, -93750, 25000),
                ExpectedData(command_time + 4.0, -75000, 50000),
                ExpectedData(command_time + 4.5, -44118, 66421),
                ExpectedData(command_time + 5.0, -17157, 41421),
                ExpectedData(command_time + 5.5, -2697, 16421),
                ExpectedData(command_time + 6.0, 0, 0),
            ]:
                await self.assert_position_and_velocity(expected_data)

    async def test_pos_stop_while_at_max_speed(self) -> None:
        async with self.create_emulated_motor():
            command_time = self.t = datetime.now().astimezone().timestamp()
            await self.emulated_motor_controller.move(
                target_position=1000000 * self.conversion_factor
            )
            for expected_data in [
                ExpectedData(command_time + 1.0, 25000, 50000),
                ExpectedData(command_time + 2.0, 100000, 100000),
                ExpectedData(command_time + 3.0, 200000, 100000),
            ]:
                await self.assert_position_and_velocity(expected_data)
            await self.emulated_motor_controller.stop_motion()
            for expected_data in [
                ExpectedData(command_time + 3.1, 209750, 95000),
                ExpectedData(command_time + 4.0, 275000, 50000),
                ExpectedData(command_time + 5.0, 300000, 0),
            ]:
                await self.assert_position_and_velocity(expected_data)

    async def test_pos_stop_while_speeding_up(self) -> None:
        async with self.create_emulated_motor():
            command_time = self.t = datetime.now().astimezone().timestamp()
            await self.emulated_motor_controller.move(
                target_position=1000000 * self.conversion_factor
            )
            for expected_data in [
                ExpectedData(command_time + 1.0, 25000, 50000),
                ExpectedData(command_time + 1.5, 56250, 75000),
            ]:
                await self.assert_position_and_velocity(expected_data)
            await self.emulated_motor_controller.stop_motion()
            for expected_data in [
                ExpectedData(command_time + 1.6, 63500, 70000),
                ExpectedData(command_time + 1.7, 70250, 65000),
                ExpectedData(command_time + 2.0, 87500, 50000),
                ExpectedData(command_time + 2.5, 106250, 25000),
                ExpectedData(command_time + 3.0, 112500, 0),
            ]:
                await self.assert_position_and_velocity(expected_data)

    async def test_pos_stop_while_slowing_down(self) -> None:
        async with self.create_emulated_motor():
            command_time = self.t = datetime.now().astimezone().timestamp()
            await self.emulated_motor_controller.move(
                target_position=100000 * self.conversion_factor
            )
            for expected_data in [
                ExpectedData(command_time + 0.5, 6250, 25000),
                ExpectedData(command_time + 1.0, 25000, 50000),
                ExpectedData(command_time + 1.5, 55882, 66421),
                ExpectedData(command_time + 2.0, 82843, 41421),
            ]:
                await self.assert_position_and_velocity(expected_data)
            await self.emulated_motor_controller.stop_motion()
            for expected_data in [
                ExpectedData(command_time + 2.5, 97303, 16421),
                ExpectedData(command_time + 3.0, 100000, 0),
            ]:
                await self.assert_position_and_velocity(expected_data)

    async def test_neg_stop_while_at_max_speed(self) -> None:
        async with self.create_emulated_motor():
            command_time = self.t = datetime.now().astimezone().timestamp()
            await self.emulated_motor_controller.move(
                target_position=-1000000 * self.conversion_factor
            )
            for expected_data in [
                ExpectedData(command_time + 1.0, -25000, -50000),
                ExpectedData(command_time + 2.0, -100000, -100000),
                ExpectedData(command_time + 3.0, -200000, -100000),
            ]:
                await self.assert_position_and_velocity(expected_data)
            await self.emulated_motor_controller.stop_motion()
            for expected_data in [
                ExpectedData(command_time + 3.1, -209750, -95000),
                ExpectedData(command_time + 4.0, -275000, -50000),
                ExpectedData(command_time + 5.0, -300000, 0),
            ]:
                await self.assert_position_and_velocity(expected_data)

    async def test_neg_stop_while_speeding_up(self) -> None:
        async with self.create_emulated_motor():
            command_time = self.t = datetime.now().astimezone().timestamp()
            await self.emulated_motor_controller.move(
                target_position=-1000000 * self.conversion_factor
            )
            for expected_data in [
                ExpectedData(command_time + 1.0, -25000, -50000),
                ExpectedData(command_time + 1.5, -56250, -75000),
            ]:
                await self.assert_position_and_velocity(expected_data)
            await self.emulated_motor_controller.stop_motion()
            for expected_data in [
                ExpectedData(command_time + 1.6, -63500, -70000),
                ExpectedData(command_time + 1.7, -70250, -65000),
                ExpectedData(command_time + 2.0, -87500, -50000),
                ExpectedData(command_time + 2.5, -106250, -25000),
                ExpectedData(command_time + 3.0, -112500, 0),
            ]:
                await self.assert_position_and_velocity(expected_data)

    async def test_neg_stop_while_slowing_down(self) -> None:
        async with self.create_emulated_motor():
            command_time = self.t = datetime.now().astimezone().timestamp()
            await self.emulated_motor_controller.move(
                target_position=-100000 * self.conversion_factor
            )
            for expected_data in [
                ExpectedData(command_time + 0.5, -6250, -25000),
                ExpectedData(command_time + 1.0, -25000, -50000),
                ExpectedData(command_time + 1.5, -55882, -66421),
                ExpectedData(command_time + 2.0, -82843, -41421),
            ]:
                await self.assert_position_and_velocity(expected_data)
            await self.emulated_motor_controller.stop_motion()
            for expected_data in [
                ExpectedData(command_time + 2.5, -97303, -16421),
                ExpectedData(command_time + 3.0, -100000, 0),
            ]:
                await self.assert_position_and_velocity(expected_data)

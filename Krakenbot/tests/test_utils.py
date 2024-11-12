from decimal import Decimal
import asyncio
import requests

from django.test import TestCase

from Krakenbot import settings
from Krakenbot.utils import acc_calc, clean_kraken_pair, usd_to_gbp


class CalculationTest(TestCase):
	def test_addition(self):
		self.assertIsInstance(acc_calc(50, '+', 800), Decimal)
		self.assertEqual(acc_calc(50, '+', 800), 850)
		self.assertEqual(acc_calc(50, '+', '800'), 850)
		self.assertEqual(acc_calc('50', '+', 800), 850)
		self.assertEqual(acc_calc('50', '+', '800'), 850)
		self.assertEqual(acc_calc('0.111222333111222333', '+', '0.111222333111222333'), Decimal('0.222444666222444666')) # Check 18 decimal places
		self.assertEqual(acc_calc('0.1234', '+', 0.1234, 2), Decimal('0.24')) # Truncated instead of rounding


	def test_subtraction(self):
		self.assertIsInstance(acc_calc(50, '-', 800), Decimal)
		self.assertEqual(acc_calc(50, '-', 800), -750)
		self.assertEqual(acc_calc(50, '-', '800'), -750)
		self.assertEqual(acc_calc('50', '-', 800), -750)
		self.assertEqual(acc_calc('50', '-', '800'), -750)
		self.assertEqual(acc_calc('0.222444666222444666', '-', '0.111222333111222333'), Decimal('0.111222333111222333')) # Check 18 decimal places
		self.assertEqual(acc_calc('0.5089', '-', 0.1911, 2), Decimal('0.31')) # Truncated instead of rounding


	def test_multiplication(self):
		self.assertIsInstance(acc_calc(50, '*', 800), Decimal)
		self.assertEqual(acc_calc(50, '*', 800), 40000)
		self.assertEqual(acc_calc(50, '*', '800'), 40000)
		self.assertEqual(acc_calc('50', '*', 800), 40000)
		self.assertEqual(acc_calc('50', '*', '800'), 40000)
		self.assertEqual(acc_calc('0.111222333111222333', '*', '0.111222333111222333'), Decimal('0.012370407382703703')) # Check 18 decimal places
		self.assertEqual(acc_calc('0.25', '*', 0.25, 2), Decimal('0.06')) # Truncated instead of rounding


	def test_division(self):
		self.assertIsInstance(acc_calc(50, '/', 800), Decimal)
		self.assertEqual(acc_calc(50, '/', 800), Decimal('0.0625'))
		self.assertEqual(acc_calc(50, '/', '800'), Decimal('0.0625'))
		self.assertEqual(acc_calc('50', '/', 800), Decimal('0.0625'))
		self.assertEqual(acc_calc('50', '/', '800'), Decimal('0.0625'))
		self.assertEqual(acc_calc('5', '/', '52350'), Decimal('0.000095510983763132')) # Check 18 decimal places
		self.assertEqual(acc_calc(5, '/', 52350, 2), Decimal('0.00')) # Truncated instead of rounding


	def test_floor_division(self):
		self.assertIsInstance(acc_calc(800, '//', 90), Decimal)
		self.assertEqual(acc_calc(800, '//', 90), 8)
		self.assertEqual(acc_calc(800, '//', '90'), 8)
		self.assertEqual(acc_calc('800', '//', 90), 8)
		self.assertEqual(acc_calc('800', '//', '90'), 8)


	def test_modulus(self):
		self.assertIsInstance(acc_calc(800, '%', 90), Decimal)
		self.assertEqual(acc_calc(800, '%', 90), 80)
		self.assertEqual(acc_calc(800, '%', '90'), 80)
		self.assertEqual(acc_calc('800', '%', 90), 80)
		self.assertEqual(acc_calc('800', '%', '90'), 80)


	def test_equal(self):
		self.assertIsInstance(acc_calc(800, '==', 800), bool)
		self.assertEqual(acc_calc(800, '==', 800), True)
		self.assertEqual(acc_calc(800, '==', '800'), True)
		self.assertEqual(acc_calc('800', '==', 800), True)
		self.assertEqual(acc_calc('800', '==', '800'), True)
		self.assertEqual(acc_calc('800', '==', '80'), False)


	def test_not_equal(self):
		self.assertIsInstance(acc_calc(800, '!=', 800), bool)
		self.assertEqual(acc_calc(800, '!=', 800), False)
		self.assertEqual(acc_calc(800, '!=', '800'), False)
		self.assertEqual(acc_calc('800', '!=', 800), False)
		self.assertEqual(acc_calc('800', '!=', '800'), False)
		self.assertEqual(acc_calc('800', '!=', '80'), True)


	def test_greater(self):
		self.assertIsInstance(acc_calc(800, '>', 800), bool)
		self.assertEqual(acc_calc(800, '>', 800), False)
		self.assertEqual(acc_calc(800, '>', '800'), False)
		self.assertEqual(acc_calc('800', '>', 800), False)
		self.assertEqual(acc_calc('800', '>', '800'), False)
		self.assertEqual(acc_calc('800', '>', '80'), True)
		self.assertEqual(acc_calc('80', '>', '800'), False)


	def test_greater_equal(self):
		self.assertIsInstance(acc_calc(800, '>=', 800), bool)
		self.assertEqual(acc_calc(800, '>=', 800), True)
		self.assertEqual(acc_calc(800, '>=', '800'), True)
		self.assertEqual(acc_calc('800', '>=', 800), True)
		self.assertEqual(acc_calc('800', '>=', '800'), True)
		self.assertEqual(acc_calc('800', '>=', '80'), True)
		self.assertEqual(acc_calc('80', '>=', '800'), False)


	def test_less(self):
		self.assertIsInstance(acc_calc(800, '<', 800), bool)
		self.assertEqual(acc_calc(800, '<', 800), False)
		self.assertEqual(acc_calc(800, '<', '800'), False)
		self.assertEqual(acc_calc('800', '<', 800), False)
		self.assertEqual(acc_calc('800', '<', '800'), False)
		self.assertEqual(acc_calc('800', '<', '80'), False)
		self.assertEqual(acc_calc('80', '<', '800'), True)


	def test_less_equal(self):
		self.assertIsInstance(acc_calc(800, '<=', 800), bool)
		self.assertEqual(acc_calc(800, '<=', 800), True)
		self.assertEqual(acc_calc(800, '<=', '800'), True)
		self.assertEqual(acc_calc('800', '<=', 800), True)
		self.assertEqual(acc_calc('800', '<=', '800'), True)
		self.assertEqual(acc_calc('800', '<=', '80'), False)
		self.assertEqual(acc_calc('80', '<=', '800'), True)


class UtilityTest(TestCase):
	def test_usd_to_gbp(self):
		rate = asyncio.run(usd_to_gbp())
		self.assertAlmostEqual(rate, Decimal(0.75), delta=0.07)


	def test_clean_kraken_pair(self):
		result = requests.get(settings.KRAKEN_PAIR_API).json()
		result = clean_kraken_pair(result)
		self.assertIn('BTCUSD', result)
		self.assertNotIn('BTCZUSD', result)
		self.assertNotIn('XXBTUSD', result)
		self.assertNotIn('XXBTZUSD', result)

		result = requests.get(settings.KRAKEN_OHLC_API, { 'pair': 'GBPUSD' }).json()
		result = clean_kraken_pair(result)
		self.assertIn('GBPUSD', result)
		self.assertNotIn('GBPZUSD', result)
		self.assertNotIn('ZGBPUSD', result)
		self.assertNotIn('ZGBPZUSD', result)

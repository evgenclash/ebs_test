import datetime
from datetime import timedelta
from time import time

from django.test import TestCase
from rest_framework.reverse import reverse
from rest_framework.test import APIClient


class TestProducts(TestCase):

    def setUp(self) -> None:
        self.client = APIClient()

    def _add_product(self):
        response = self.client.post(reverse('product-list'), data={
            'name': 'Product name',
            'sku': 'SKU1',
            'description': 'Product description',
        }, format="json")

        self.assertEqual(response.status_code, 201)
        self.assertIn('id', response.data)
        return response.data['id']

    def _add_price(self, product_id, start_date, end_date, price):
        response = self.client.post(reverse('product-price-list'), data={
            'product': product_id,
            'start_date': start_date,
            'end_date': end_date,
            'price': price,
        }, format="json")

        self.assertEqual(response.status_code, 201)
        self.assertIn('id', response.data)

    def _check_price(self, product_id, start_date, end_date, price, days):
        # Request GET /products/stats/ to get price stats
        response = self.client.get(reverse('product-stats'), data={
            'product': product_id,
            'start_date': start_date,
            'end_date': end_date
        })

        self.assertEqual(response.status_code, 200)

        # Check price calculation
        self.assertIn('price', response.data)
        self.assertEqual(response.data['price'], price)

        # Check number of days in period
        self.assertIn('days', response.data)
        self.assertEqual(response.data['days'], days)

    def test_stage_1(self):
        product_id = self._add_product()
        self._add_price(product_id, '2022-01-01', '2022-01-20', 10)
        self._check_price(product_id, '2022-01-01', '2022-01-20', 10, 20)
        self._check_price(product_id, '2022-01-10', '2022-01-15', 10, 6)
        self._check_price(product_id, '2022-01-19', '2022-01-22', 10, 4)

    def test_stage_2(self):
        product_id = self._add_product()
        self._add_price(product_id, '2022-01-01', '2022-01-01', 10)
        self._add_price(product_id, '2022-01-02', '2022-01-02', 20)
        self._add_price(product_id, '2022-01-03', '2022-01-03', 30)

        self._add_price(product_id, '2022-01-01', '2022-01-03', 40)

        self._check_price(product_id, '2022-01-01', '2022-01-03', 40, 3)

    def test_stage_3(self):
        product_id = self._add_product()
        self._add_price(product_id, '2022-01-01', '2022-01-10', 10)
        self._add_price(product_id, '2022-01-11', '2022-01-20', 20)

        self._add_price(product_id, '2022-01-05', '2022-01-15', 30)
        self._check_price(product_id, '2022-01-06', '2022-01-15', 30, 10)

        self._add_price(product_id, '2022-01-01', None, 10)
        self._check_price(product_id, '2022-01-06', '2022-01-15', 10, 10)

    def test_stage_4(self):
        product_id = self._add_product()
        self._add_price(product_id, '2022-01-01', '2022-01-5', 10)
        self._add_price(product_id, '2022-01-06', '2022-01-10', 15)
        self._add_price(product_id, '2022-01-11', '2022-01-15', 20)

        self._add_price(product_id, '2022-01-04', '2022-01-13', 30)
        self._check_price(product_id, '2022-01-03', '2022-01-14', 27.5, 12)

    def test_stage_5(self):
        product_id = self._add_product()

        start_date = datetime.datetime(year=2022, month=1, day=1)
        i = 1
        for i in range(1, 800):
            start_time = time()
            before_date = start_date - timedelta(days=100)
            self._add_price(product_id, before_date.strftime('%Y-%m-%d'), start_date.strftime('%Y-%m-%d'), 20)
            self.assertLess(time() - start_time, 0.1)
            start_date = start_date + timedelta(days=1)

        start_time = time()
        self._check_price(product_id, '2022-01-01', start_date.strftime('%Y-%m-%d'), 20, i + 1)
        self.assertLess(time() - start_time, 1)

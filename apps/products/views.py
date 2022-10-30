from copy import deepcopy
from datetime import datetime, timedelta

from django.db.models import Q
from drf_util.views import BaseViewSet, BaseCreateModelMixin, BaseListModelMixin
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny

from apps.products.models import Product, PriceInterval
from apps.products.serializers import ProductSerializer, PriceIntervalSerializer
from rest_framework.response import Response


def get_price_intervals(end, product, start):
    return PriceInterval.objects.filter(
        Q(product_id=product,
          start_date__lte=start,
          end_date__gte=start) |
        Q(product_id=product,
          start_date__lte=end,
          end_date__gte=end) |
        Q(product_id=product,
          start_date__gte=start,
          end_date__lte=end)
    )


def calculate_average_price(end, intervals, start):
    total_price = 0
    total_days = 0

    for interval in intervals:
        interval_days = (min(interval.end_date, end) - max(interval.start_date, start)).days + 1
        total_price += interval.price * interval_days
        total_days += interval_days

    if not total_days:
        return 0, 0

    days = (end - start).days + 1
    res = total_price / total_days

    return days, res


class ProductViewSet(BaseListModelMixin, BaseCreateModelMixin, BaseViewSet):
    permission_classes = AllowAny,
    authentication_classes = ()
    serializer_class = ProductSerializer
    queryset = Product.objects.all()

    @action(methods=["get"], detail=False)
    def stats(self, request):
        start = datetime.strptime(request.query_params.get('start_date'), "%Y-%m-%d").date()
        end = datetime.strptime(request.query_params.get('end_date'), "%Y-%m-%d").date()
        product = request.query_params.get('product')

        intervals = get_price_intervals(end, product, start)

        days, res = calculate_average_price(end, intervals, start)

        return Response({'price': res, "days": days}, status=200)


class ProductPriceViewSet(BaseListModelMixin, BaseCreateModelMixin, BaseViewSet):
    permission_classes = AllowAny,
    authentication_classes = ()
    serializer_class = PriceIntervalSerializer
    queryset = PriceInterval.objects.all()

    def create(self, request, *args, **kwargs):
        if not request.data["end_date"]:
            request.data["end_date"] = "9999-12-31"
        serializer = self.get_serializer_create(data=request.data)
        serializer.is_valid(raise_exception=True)

        create_intervals, update_intervals = self.define_new_intervals(request)

        PriceInterval.objects.bulk_update(update_intervals, ["start_date", "end_date"])
        PriceInterval.objects.bulk_create(create_intervals)
        instance = self.perform_create(serializer, **kwargs)

        serializer_display = self.get_serializer(instance)
        return Response(serializer_display.data, status=status.HTTP_201_CREATED)

    def define_new_intervals(self, request):
        new_start = datetime.strptime(request.data["start_date"], "%Y-%m-%d").date()
        new_end = datetime.strptime(request.data["end_date"], "%Y-%m-%d").date()

        intervals_for_same_product = get_price_intervals(new_end, request.data["product"], new_start)

        update_intervals = []
        create_intervals = []

        for interval in intervals_for_same_product:
            if self.is_only_start_included(interval, new_start, new_end):
                interval.end_date = new_start - timedelta(days=1)
                update_intervals.append(interval)
            elif self.is_new_interval_included(interval, new_start, new_end):
                self.add_modified_intervals(create_intervals, interval, new_end, new_start,
                                            update_intervals)
            elif self.is_only_end_included(interval, new_start, new_end):
                interval.start_date = new_end + timedelta(days=1)
                update_intervals.append(interval)
            elif self.is_included_in_new_interval(interval, new_start, new_end):
                interval.delete()

        return create_intervals, update_intervals

    def is_only_start_included(self, interval, new_start, new_end):
        return interval.start_date < new_start <= interval.end_date <= new_end

    def is_new_interval_included(self, interval, new_start, new_end):
        return interval.start_date < new_start and interval.end_date > new_end

    def is_only_end_included(self, interval, new_start, new_end):
        return new_start <= interval.start_date <= new_end < interval.end_date

    def is_included_in_new_interval(self, interval, new_start, new_end):
        return new_start <= interval.start_date and new_end >= interval.end_date

    def add_modified_intervals(self, create_intervals, interval, new_end, new_start, update_intervals):
        second_interval = deepcopy(interval)
        interval.end_date = new_start - timedelta(days=1)
        second_interval.start_date = new_end + timedelta(days=1)

        if second_interval.end_date != second_interval.start_date:
            second_interval.id = None
            create_intervals.append(second_interval)
        if interval.end_date != second_interval.start_date:
            update_intervals.append(interval)
        else:
            interval.delete()

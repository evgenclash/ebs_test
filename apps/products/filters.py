from django_filters import FilterSet, ModelChoiceFilter, DateFilter

from apps.products.models import Product


class PriceStatsFilter(FilterSet):
    product = ModelChoiceFilter(queryset=Product.objects.all())
    start_date = DateFilter(method='filter_stats')
    end_date = DateFilter(method='filter_stats')

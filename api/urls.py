from django.urls import include, path

from .account_views import ClaimView, MeView
from .proposal_views import MyProposalsView, MyProposalView, ProposalCreateView, ProposalFormView
from .views import (
    MountainView,
    MountainRoutesView,
    MountainAscentsView,
    MountainReferencesView,
    MountainNomenclaturaView,
    RouteView,
    RouteNameView,
    RouteTableView,
    RouteReferencesView,
    RouteAscentsView,
    AscentView,
    AscentTableView,
    AscentReferencesView,
    AndinistView,
    AndinistBasicView,
    AndinistTableView,
    AndinistReferencesView,
    AndinistAscentsView,
    ImageView,
    ImagesView,
    CountriesView,
    RegionsView,
    MountainPrefixesView,
    MountainGroupsView,
    MountainsView,
    sitemap_ids,
)

urlpatterns = [
    path("mountains/", MountainsView.as_view(), name="mountains"),
    path("mountain/<int:pk>/", MountainView.as_view(), name="mountain"),
    path(
        "mountain/<int:pk>/routes/",
        MountainRoutesView.as_view(),
        name="mountain-routes",
    ),
    path(
        "mountain/<int:pk>/ascents/",
        MountainAscentsView.as_view(),
        name="mountain-ascents",
    ),
    path(
        "mountain/<int:pk>/references/",
        MountainReferencesView.as_view(),
        name="mountain-references",
    ),
    path(
        "mountain/<int:pk>/nomenclatura/",
        MountainNomenclaturaView.as_view(),
        name="mountain-nomenclatura",
    ),
    path("route/<int:pk>/", RouteView.as_view(), name="route"),
    path("route/<int:pk>/name/", RouteNameView.as_view(), name="route-name"),
    path("route/table/", RouteTableView.as_view(), name="route-table"),
    path(
        "route/<int:pk>/references/",
        RouteReferencesView.as_view(),
        name="route-references",
    ),
    path("route/<int:pk>/ascents/", RouteAscentsView.as_view(), name="route-ascents"),
    path("ascent/<int:pk>/", AscentView.as_view(), name="ascent"),
    path("ascent/table/", AscentTableView.as_view(), name="ascent-table"),
    path(
        "ascent/<int:pk>/references/",
        AscentReferencesView.as_view(),
        name="ascent-references",
    ),
    path("andinist/<int:pk>/", AndinistView.as_view(), name="andinist"),
    path(
        "andinist/<int:pk>/basic/", AndinistBasicView.as_view(), name="andinist-basic"
    ),
    path("andinist/table/", AndinistTableView.as_view(), name="andinist-table"),
    path(
        "andinist/<int:pk>/references/",
        AndinistReferencesView.as_view(),
        name="andinist-references",
    ),
    path(
        "andinist/<int:pk>/ascents/",
        AndinistAscentsView.as_view(),
        name="andinist-ascents",
    ),
    path("image/<int:pk>/", ImageView.as_view(), name="image"),
    path("images/", ImagesView.as_view(), name="images"),
    path("countries/", CountriesView.as_view(), name="countries"),
    path("regions/", RegionsView.as_view(), name="regions"),
    path("prefixes/", MountainPrefixesView.as_view(), name="prefixes"),
    path("groups/", MountainGroupsView.as_view(), name="groups"),
    path("sitemap/", sitemap_ids, name="sitemap"),
    # Accounts: login/signup/passwords (allauth) and the user's own data
    path("_allauth/", include("allauth.headless.urls")),
    path("me/", MeView.as_view(), name="me"),
    path("me/claim/", ClaimView.as_view(), name="me-claim"),
    # Proposed changes (reviewed by editors in the admin)
    path("proposals/", ProposalCreateView.as_view(), name="proposal-create"),
    path("proposals/form/<str:slug>/<str:target>/", ProposalFormView.as_view(), name="proposal-form"),
    path("me/proposals/", MyProposalsView.as_view(), name="my-proposals"),
    path("me/proposals/<int:pk>/", MyProposalView.as_view(), name="my-proposal"),
]

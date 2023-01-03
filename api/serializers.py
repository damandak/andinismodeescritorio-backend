from rest_framework import serializers
from cerros.models import (
    MountainPrefix,
    Mountain,
    Country,
    Route,
    Ascent,
    Andinist,
    Reference,
    NomenclaturaSummit,
    IGMMap,
    Image
)

class MountainSerializer(serializers.ModelSerializer):
    prefix = serializers.StringRelatedField()
    first_absolute_name = serializers.SerializerMethodField()
    first_absolute_date = serializers.SerializerMethodField()
    first_absolute_team = serializers.SerializerMethodField()
    class Meta:
        model = Mountain
        fields = [
            'id',
            'prefix',
            'name',
            'latitude',
            'longitude',
            'altitude',
            'altitude_igm',
            'altitude_arg',
            'altitude_gps',
            'main_altitude_source',
            'parent_mountain',
            'nomenclatura_mountain',
            'ref_ahb',
            'ref_wikiexplora',
            'countries',
            'regions',
            'mountain_group',
            'first_absolute',
            'first_absolute_name',
            'first_absolute_date',
            'first_absolute_team',
            'unregistered_non_sport_ascent',
            'main_image',
        ]
    
    def get_first_absolute_name(self, obj):
        if obj.first_absolute:
            return obj.first_absolute.name
        return None
    
    def get_first_absolute_date(self, obj):
        if obj.first_absolute:
            return obj.first_absolute.date_tostring()
        return None

    def get_first_absolute_team(self, obj):
        if obj.first_absolute:
            return [(a.id, str(a)) for a in obj.first_absolute.andinists.all()]
        else:
            return None

class MapMountainSerializer(serializers.ModelSerializer):
    prefix = serializers.StringRelatedField()
    class Meta:
        model = Mountain
        fields = ['id', 'prefix', 'name', 'latitude', 'longitude', 'altitude']

class BasicMountainSerializer(serializers.ModelSerializer):
    prefix = serializers.StringRelatedField()
    countries = serializers.SlugRelatedField(slug_field='name', many=True, read_only=True)
    regions = serializers.SlugRelatedField(slug_field='name', many=True, read_only=True)
    mountain_group = serializers.SlugRelatedField(slug_field='name', many=True, read_only=True)
    class Meta:
        model = Mountain
        fields = ['id', 'prefix', 'name', 'latitude', 'longitude', 'altitude', 'parent_mountain', 'countries', 'regions', 'mountain_group']
        extra_kwargs = {
          'countries': {'required': False},
          'regions': {'required': False},
          'mountain_group': {'required': False}
        }

class FullMountainsSerializer(serializers.ModelSerializer):
    prefix = serializers.StringRelatedField()
    class Meta:
        model = Mountain
        fields = '__all__'

class CountriesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = '__all__'

class RouteNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = Route
        fields = ['id', 'name']

class AscentsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ascent
        fields = ['id', 'name', 'route', 'completed', 'andinists', 'support_andinists', 'date', 'date_format']

class AndinistBasicSerializer(serializers.ModelSerializer):
    fullname = serializers.SerializerMethodField()
    class Meta:
        model = Andinist
        fields = ['id', 'fullname']

    def get_fullname(self, obj):
        return str(obj)

class ReferencesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reference
        fields = ['publication_name', 'publication_edition', 'publication_year', 'title', 'author', 'page', 'url']

class NomenclaturaSummitSerializer(serializers.ModelSerializer):
    igm_rectangle_name = serializers.SerializerMethodField()
    class Meta:
        model = NomenclaturaSummit
        fields = ['id_nomenclatura', 'cod_revision', 'name', 'altitude_igm', 'latitude', 'longitude', 'observations', 'comment', 'igm_rectangle_name']

    def get_igm_rectangle_name(self, obj):
        return obj.igm_rectangle.name

class RouteTableSerializer(serializers.ModelSerializer):
    parent_route_name = serializers.SerializerMethodField()
    mountain_name = serializers.SerializerMethodField()
    difficulty = serializers.SerializerMethodField()
    first_ascent_info = serializers.SerializerMethodField()

    class Meta:
        model = Route
        fields = ['id', 'parent_route', 'parent_route_name', 'name', 'mountain', 'mountain_name', 'summit', 'difficulty', 'first_ascent_info']

    def get_parent_route_name(self, obj):
        if obj.parent_route:
            return obj.parent_route.name
        else:
            return None
    
    def get_mountain_name(self, obj):
        return obj.mountain.prefix.prefix + " " + obj.mountain.name
    
    def get_difficulty(self, obj):
        difficulty = ""
        if obj.alpine_grade:
            difficulty += obj.alpine_grade.name
        if obj.aid_climbing_grade:
            difficulty += " " + obj.aid_climbing_grade.name
        if obj.ice_climbing_grade:
            difficulty += " " + obj.ice_climbing_grade.name
        if obj.rock_climbing_grade:
            difficulty += " " + obj.rock_climbing_grade.name
        return difficulty

    def get_first_ascent_info(self, obj):
        return obj.first_ascent_year()
        
class RouteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Route
        fields = ['id', 'parent_route', 'name', 'mountain', 'summit', 'ascended', 'first_ascent', 'unregistered_non_sport_ascent', 'unregistered_sport_ascent', 'alpine_grade', 'aid_climbing_grade', 'ice_climbing_grade', 'rock_climbing_grade', 'description', 'kml', 'gpx', 'references', 'notes']

class AscentTableSerializer(serializers.ModelSerializer):
    route_name = serializers.SerializerMethodField()
    mountain = serializers.SerializerMethodField()
    mountain_name = serializers.SerializerMethodField()
    andinists = serializers.SerializerMethodField()
    date_tostr = serializers.SerializerMethodField()

    class Meta:
        model = Ascent
        fields = ['id', 'name', 'route', 'route_name', 'mountain', 'mountain_name', 'andinists', 'completed', 'date_tostr']

    def get_route_name(self, obj):
        return obj.route.name
    
    def get_mountain(self, obj):
        return obj.route.mountain.id

    def get_mountain_name(self, obj):
        return obj.route.mountain.prefix.prefix + " " + obj.route.mountain.name
    
    def get_andinists(self, obj):
        # return tuples with andinist id and fullname
        return [(a.id, str(a)) for a in obj.andinists.all()]

    def get_date_tostr(self, obj):
        return obj.date_tostring()

class AndinistTableSerializer(serializers.ModelSerializer):
    fullname = serializers.SerializerMethodField()
    nationalities_tostr = serializers.SerializerMethodField()
    clubs_tostr = serializers.SerializerMethodField()

    class Meta:
        model = Andinist
        fields = ['id', 'fullname', 'nationalities_tostr', 'clubs_tostr', 'ascent_count', 'new_routes_count', 'first_ascent_count']
    
    def get_fullname(self, obj):
        return str(obj)

    def get_nationalities_tostr(self, obj):
        result = ""
        for c in obj.nationalities.all():
            result += c.name + ", "
        return result[:-2]

    def get_clubs_tostr(self, obj):
        result = ""
        for c in obj.clubs.all():
            result += c.name + ", "
        return result[:-2]

class AscentSerializer(serializers.ModelSerializer):
    route_name = serializers.SerializerMethodField()
    mountain = serializers.SerializerMethodField()
    mountain_name = serializers.SerializerMethodField()
    andinists = serializers.SerializerMethodField()
    support_andinists = serializers.SerializerMethodField()
    date_tostr = serializers.SerializerMethodField()

    class Meta:
        model = Ascent
        fields = ['id', 'name', 'route', 'route_name', 'mountain', 'mountain_name', 'andinists', 'support_andinists', 'completed', 'date_tostr', 'is_first_ascent', 'new_route']

    def get_route_name(self, obj):
        return obj.route.name

    def get_mountain(self, obj):
        return obj.route.mountain.id

    def get_mountain_name(self, obj):
        return obj.route.mountain.prefix.prefix + " " + obj.route.mountain.name

    def get_andinists(self, obj):
        # return tuples with andinist id and fullname
        return [(a.id, str(a)) for a in obj.andinists.all()]

    def get_support_andinists(self, obj):
        # return tuples with andinist id and fullname
        return [(a.id, str(a)) for a in obj.support_andinists.all()]
    
    def get_date_tostr(self, obj):
        return obj.date_tostring()
        
class RouteSerializer(serializers.ModelSerializer):
    parent_route_name = serializers.SerializerMethodField()
    mountain_name = serializers.SerializerMethodField()
    first_ascent_name = serializers.SerializerMethodField()
    first_ascent_date = serializers.SerializerMethodField()
    first_ascent_team = serializers.SerializerMethodField()

    class Meta:
        model = Route
        fields = ['id', 'parent_route', 'parent_route_name', 'name', 'mountain', 'mountain_name', 'summit', 'ascended', 'first_ascent', 'first_ascent_name', 'first_ascent_date', 'first_ascent_team', 'unregistered_non_sport_ascent', 'unregistered_sport_ascent', 'alpine_grade', 'aid_climbing_grade', 'ice_climbing_grade', 'rock_climbing_grade', 'description', 'kml', 'gpx', 'notes']

    def get_parent_route_name(self, obj):
        if obj.parent_route:
            return obj.parent_route.name
        else:
            return None

    def get_mountain_name(self, obj):
        return obj.mountain.prefix.prefix + " " + obj.mountain.name

    def get_first_ascent_name(self, obj):
        if obj.first_ascent:
            return obj.first_ascent.name
        else:
            return None

    def get_first_ascent_date(self, obj):
        if obj.first_ascent:
            return obj.first_ascent.date_tostring()
        else:
            return None

    def get_first_ascent_team(self, obj):
        if obj.first_ascent:
            return [(a.id, str(a)) for a in obj.first_ascent.andinists.all()]
        else:
            return None

class AndinistSerializer(serializers.ModelSerializer):
    nationalities_tostr = serializers.SerializerMethodField()
    clubs_tostr = serializers.SerializerMethodField()

    class Meta:
        model = Andinist
        fields = ['id', 'name', 'surname', 'gender', 'nationalities_tostr', 'clubs_tostr', 'ascent_count', 'new_routes_count', 'first_ascent_count']

    def get_nationalities_tostr(self, obj):
        result = ""
        for c in obj.nationalities.all():
            result += c.name + ", "
        return result[:-2]

    def get_clubs_tostr(self, obj):
        result = ""
        for c in obj.clubs.all():
            result += c.name + ", "
        return result[:-2]

class ImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Image
        fields = ['id', 'name', 'image', 'author', 'description', 'date_captured']


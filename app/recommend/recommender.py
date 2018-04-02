from app.filters.base_filter import Bridge


def get_recommendation():
    return {
        "id": Bridge.id()
    }

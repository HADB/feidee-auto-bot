from datetime import datetime


def datetime_hook(json_dict):
    for (key, value) in json_dict.items():
        try:
            json_dict[key] = datetime.strptime(value, "%Y-%m-%d %H:%M")
        except:
            pass
    return json_dict


def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, datetime):
        return datetime.strftime(obj, "%Y-%m-%d %H:%M")
    raise TypeError("Type %s not serializable" % type(obj))

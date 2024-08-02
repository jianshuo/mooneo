# Author: Jianshuo Wang
# Date: 2024-07-25
# Version: 0.1
# This small library helps to build functions to interact with Elasticsearch
# It is suggested that you inherit the Data class to build your own data class

import time
from copy import copy

from elasticsearch import Elasticsearch
from elasticsearch.exceptions import NotFoundError
from elasticsearch_dsl import A, Q, Search


class RequiredFieldMissingException(Exception):
    pass


class Field:
    """Define data fields"""

    def __init__(self, name, required=False, hidden=False, default=None, type=None):
        self.name = name
        self.required = required
        self.hidden = hidden
        self.default = default
        self.type = type or "str"

    def __repr__(self):
        return (
            f"<{self.__class__.__name__} name={self.name}, "
            f" required={self.required}>"
        )


class Response:
    """The response data from find function"""

    def __init__(self):
        self.data = []
        self.count = 0

    def __iter__(self):
        return iter(self.data)

    def __len__(self):
        return len(self.data)

    def __getitem__(self, n):
        return self.data[n]

    def first(self, **kwargs):
        """Find the only one result from search"""
        for result in self.data:
            return result
        return None

    def __str__(self):
        return f"{self.__class__.__name__} {len(self.data)}/{self.count}"


class Edge:
    """Define edges"""

    def __init__(self, name):
        self.name = name


# This is the test ES Server managed by 纳什
# jianshuo@100031339132
# 子账号 ID: 100037619115
# 主账号 ID: 100031339132
ES_SERVER = "es-nluebvi0.public.tencentelasticsearch.com:9200"
ES_AUTH_USER = "elastic"
ES_AUTH_PASSWORD = "Baixing2023*"


class Data:
    """Basic core data representation"""

    index = "*"  # bugbug Not sure if this works
    fields = [
        Field("id"),
        Field("created", type="datetime"),
        Field("modified", type="datetime"),
        Field("deleted", type="bool", default=False),
    ]
    es = Elasticsearch(
        hosts=[f"https://{ES_AUTH_USER}:{ES_AUTH_PASSWORD}@{ES_SERVER}"],
        timeout=30,
        max_retries=10,
        retry_on_timeout=True,
    )

    def __init__(self, id=None):
        """Init"""
        if id:
            self.load(id)

    def load(self, id):
        """Load by id"""
        try:
            item = self.es.get(index=self.index, id=id)
            print(f'{self.__class__.__name__} ("{self.index}") getting {id}')
        except NotFoundError:
            item = None

        if item is None:
            raise FileNotFoundError(f"{self.__class__.__name__} " f"<{id}> not found")

        self.__dict__ = item["_source"].copy()
        self.id = item["_id"]
        return self

    def find(
        self,
        filter=None,
        size=20,
        page=1,
        query=None,
        query_string=None,
        sort=None,
        collapse=None,
        extra=None,
        **kwargs,
    ):

        srch = Search(index=self.index)
        srch = srch.using(self.es)

        filter = filter or {}
        for key, value in {**kwargs, **filter}.items():
            if value is None:
                continue
            srch = srch.filter("match", **{key: value})

        if query:
            srch = srch.query(Q(query))
        if query_string:
            srch = srch.query(Q("query_string", query=query_string))
        if sort:
            srch = srch.sort(sort)
        if collapse:
            srch = srch.update_from_dict({"collapse": {"field": collapse}})
            a = A("cardinality", field=collapse)
            srch.aggs.bucket("total", a)
        srch = srch.query(~Q("match", deleted=True))
        srch = srch[(page - 1) * size : page * size]

        extra = extra or {}
        srch = srch.extra(**extra)
        res = srch.execute()

        resp = Response()
        if collapse:
            resp.count = res.aggregations.total.value
        else:
            resp.count = res.hits.total.value

        for hit in res.hits:
            item = copy(self)
            item.id = hit.meta.id
            dic = hit.to_dict()
            print("SCORE", hit.meta.score)
            for field in self.field_list(exclude="id"):
                setattr(item, field.name, dic.get(field.name))
            resp.data.append(item)

        if "aggregations" in res:
            resp.aggregations = res.aggregations

        print(
            f'{self.__class__.__name__} (index="{self.index}")'
            f" search {srch.to_dict()}"
            f" <{resp}>"
        )

        return resp

    def exists(self, **kwargs):
        """Check if a data enitity exists in the search engine"""
        return self.find(**kwargs).first() is not None

    def save(self):
        self.modified = time.time()
        if not hasattr(self, "created"):
            self.created = time.time()

        for field in self.field_list():
            if field.required and not hasattr(self, field.name):
                raise RequiredFieldMissingException(
                    f"Field {field.name} is required for "
                    f"type {self.__class__.__name__}"
                )
            if field.default is not None and (
                not hasattr(self, field.name) or getattr(self, field.name) is None
            ):
                setattr(self, field.name, field.default)

        body = self.field_dict(exclude="id")

        kwargs = {"index": self.index, "body": body}

        if hasattr(self, "id"):
            kwargs["id"] = self.id

        resp = self.es.index(**kwargs)
        self.id = resp.get("_id")
        return self

    def field_list(self, exclude=None):
        """A possible fields"""
        exclude = exclude or []
        fields = Data.fields + self.fields
        return [field for field in fields if field.name not in exclude]

    def field_dict(self, exclude=None):
        """Turn self into a dict"""
        exclude = exclude or []
        return {
            key: value
            # 原因是发现title如果是'61e406800000000001026053'，这里生成的Infinity会导致save出错
            for key, value in vars(self).items()
            if key not in exclude and key in [field.name for field in self.field_list()]
        }

    def top_terms(self, field, size=10):
        """Return the top terms of the given field
        [{'key': '电影', 'doc_count': 1222}]
        """

        srch = Search(index=self.index)
        srch.aggs.bucket("top", A("terms", field=field, size=size))
        print(f"{self.__class__.__name__} is searching", srch.to_dict())
        resp = srch.execute()
        return resp.aggregations.top.buckets

    def __repr__(self):
        return f"{self.__class__.__name__} <{str(id(self))}>" f" {str(vars(self))}"

    def __eq__(self, other):
        for key, value in vars(self).items():
            if value != getattr(other, key):
                return False
        return True

    def extra(self):
        """Provide extra attrs to return to graph"""
        return {}

    def delete(self):
        self.deleted = True
        self.save()


class VectorData(Data):
    """
    Use l2norm to calculate similarity
    """

    def find(self, filter=None, **kwargs):
        """Search Vector with similarity"""
        if filter and "vector" in filter:
            query = Q(
                {
                    "function_score": {
                        "script_score": {
                            "script": {
                                "source": "1/(1+l2norm(params.queryVector,'vector'))",
                                "params": {"queryVector": filter["vector"]},
                            }
                        }
                    }
                }
            )
            return super().find(query=query, **kwargs)
        return super().find(filter=filter, **kwargs)


class Sub(Data):
    """
    Sub is a subtitle of a video.

    Attributes:
        index: The index name in the Elastic Search.
        start: The start time of the subtitle.
        end: The end time of the sub video.
        content: The content of the sub video.
        sub_start: The start time of the subtitle in the subtitle.
        sub_end: The end time of the subtitle in the subtitle.
        ts_ready: Whether the subtitle is ready to be converted to .ts
        srt_file: The name of the srt file


    Examples:
        >>> sub = Sub()
        >>> sub.index = 1
        >>> sub.start = 0
        >>> sub.end = 10
        >>> sub.content = 'hello'
        >>> sub.sub_start = 0
        >>> sub.sub_end = 10
        >>> sub.ts_ready = True
        >>> sub.save()
    """

    index = "learn_english_with_movies_index"

    fields = [
        Field("index"),
        Field("start"),
        Field("end"),
        Field("content"),
        Field("sub_start"),
        Field("sub_end"),
        Field("srt_file"),
        Field("ts_ready"),
    ]

    def __init__(self, id=None):
        super().__init__(id)

    def __str__(self):
        return self.media_url()

    def media_url(self):
        return self.srt_file + f"/{self.index}.ts"

    def id(self):
        """Generate a unique ID"""
        return f"{self.srt_file}_{self.index}"

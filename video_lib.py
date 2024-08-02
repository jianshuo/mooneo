import srt
from datetime import timedelta
from srtseg import Seg, SRTSeg
from esdata import Sub
from srtseg.adaptors import titles_to_segs
from elasticsearch_dsl import Q


def srtseg_padding(sseg: SRTSeg, padding=0):
    """Padding the SRTSeg with padding number of sentences
    For example, if padding is 1, and there is a segment with index 3
    in the original sseg, then the new sseg will have segments with index
    2, 3, 4.
    """
    rseg = SRTSeg()
    for seg in sseg.segs():
        for i in range(padding, 0, -1):
            if seg.index - i >= 0:
                sub = Sub().load(
                    id=seg.path.replace("/", "") + "_" + str(seg.index - i)
                )
                seg2 = titles_to_segs([sub])[0]
                print(i, seg2)
                rseg.segments.append(seg2)
        rseg.segments.append(seg)
        for i in range(1, padding, 1):
            sub = Sub().load(id=seg.path.replace("/", "") + "_" + str(seg.index + i))
            seg2 = titles_to_segs([sub])[0]
            print(i, seg2)
            rseg.segments.append(seg2)
    rseg._calculate_times()
    return rseg


def srtseg_from_es(query, repeat=1, padding=0):
    q = {
        "bool": {
            "filter": [
                {
                    "script": {
                        "source": "doc['end'].value - doc['start'].value < params.threshold",
                        "params": {"threshold": 3},
                    }
                }
            ]
        }
    }

    script_query = Q(
        "bool",
        filter=[
            Q(
                "script",
                script={
                    "source": "doc['end'].value - doc['start'].value < params.threshold",
                    "params": {"threshold": 5},
                },
            )
        ],
    )

    subs = list(Sub().find(query_string=query, query=script_query, size=10))
    subs1 = []
    for sub in subs:
        for _ in range(repeat):
            subs1.append(sub)

    # subs = [sub for sub in subs if sub.end - sub.start < 3]
    sseg = SRTSeg()
    sseg.segments = titles_to_segs(subs1)
    return srtseg_padding(sseg, padding)


def media_url(srt_file, index):
    path = f'{srt_file.replace(".srt", "")}/{index-1}.ts'
    return "https://mira-1255830993.cos.ap-shanghai.myqcloud.com/season2/" + path


def m3u8(segs):
    """
    Return m3u8 of the current selected content

    Args:
    Returns:
        The content of m3u8
    """
    duration = 6
    m3u8_infs = ""
    for seg in segs:
        path = media_url(seg["srt_file"], seg["index"])
        m3u8_infs += f"""#EXT-X-DISCONTINUITY
#EXTINF:{duration},
{path}
"""
    m3u8_header = f"""#EXTM3U
#EXT-X-VERSION:3
#EXT-X-MEDIA-SEQUENCE:0
#EXT-X-TARGETDURATION:10
"""
    m3u8_footer = """#EXT-X-ENDLIST\n"""
    return m3u8_header + m3u8_infs + m3u8_footer


def srtseg_from_sqlite(hits):
    """Restore SRTSeg from Chroma Hits"""
    start = 0
    sseg = SRTSeg()
    print(hits)
    for hit in hits:
        seg = Seg()
        seg_duration = hit.end - hit.start
        sub = srt.Subtitle(
            index=hit.index,
            start=timedelta(seconds=start),
            end=timedelta(seconds=start + seg_duration),
            content=hit.content,
        )
        seg.subtitle = sub
        seg.selected = True
        seg.path = hit.srt_file
        seg.start = timedelta(seconds=start)
        seg.end = timedelta(seconds=start + seg_duration)
        seg.duration = timedelta(seconds=seg_duration)
        sseg.segments.append(seg)
        start += seg_duration
    return sseg


def srtseg_from_chroma(hits, documents):
    """Restore SRTSeg from Chroma Hits"""
    start = 0
    sseg = srtseg.srtseg.SRTSeg()
    print(hits)
    for hit, doc in zip(hits, documents):
        seg = srtseg.srtseg.Seg()
        sub_duration = hit["sub_end"] - hit["sub_start"]
        seg_duration = hit["end"] - hit["start"]
        sub_offset = hit["sub_start"] - hit["start"]
        sub = srt.Subtitle(
            index=hit["index"],
            start=timedelta(seconds=start),
            end=timedelta(seconds=start + seg_duration),
            content=doc.replace("<i>", "").replace("</i>", ""),
        )
        seg.subtitle = sub
        seg.selected = True
        seg.path = hit["srt_file"]
        seg.start = timedelta(seconds=start)
        seg.end = timedelta(seconds=start + seg_duration)
        seg.duration = timedelta(seconds=seg_duration)
        sseg.segments.append(seg)
        start += seg_duration
    return sseg

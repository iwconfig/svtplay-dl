from __future__ import absolute_import

import re
import os
import logging
import sys
import time
from datetime import timedelta


from svtplay_dl.utils.text import filenamify, decode_html_entities, ensure_unicode
from svtplay_dl.utils.terminal import get_terminal_size

progress_stream = sys.stderr


class ETA(object):
    """
    An ETA class, used to calculate how long it takes to process
    an arbitrary set of items. By initiating the object with the
    number of items and continuously updating with current
    progress, the class can calculate an estimation of how long
    time remains.
    """

    def __init__(self, end, start=0):
        """
        Parameters:
        end:   the end (or size, of start is 0)
        start: the starting position, defaults to 0
        """
        self.start = start
        self.end = end
        self.pos = start

        self.now = time.time()
        self.start_time = self.now

    def update(self, pos):
        """
        Set new absolute progress position.

        Parameters:
        pos: new absolute progress
        """
        self.pos = pos
        self.now = time.time()

    def increment(self, skip=1):
        """
        Like update, but set new pos relative to old pos.

        Parameters:
        skip: progress since last update (defaults to 1)
        """
        self.update(self.pos + skip)

    @property
    def left(self):
        """
        returns: How many item remains?
        """
        return self.end - self.pos

    def __str__(self):
        """
        returns: a time string of the format HH:MM:SS.
        """
        duration = self.now - self.start_time

        # Calculate how long it takes to process one item
        try:
            elm_time = duration / (self.end - self.left)
        except ZeroDivisionError:
            return "(unknown)"

        return str(timedelta(seconds=int(elm_time * self.left)))


def progress(byte, total, extra=""):
    """ Print some info about how much we have downloaded """
    if total == 0:
        progresstr = "Downloaded %dkB bytes" % (byte >> 10)
        progress_stream.write(progresstr + '\r')
        return
    progressbar(total, byte, extra)


def progressbar(total, pos, msg=""):
    """
    Given a total and a progress position, output a progress bar
    to stderr. It is important to not output anything else while
    using this, as it relies soley on the behavior of carriage
    return (\\r).

    Can also take an optioal message to add after the
    progressbar. It must not contain newlines.

    The progress bar will look something like this:

    [099/500][=========...............................] ETA: 13:36:59

    Of course, the ETA part should be supplied be the calling
    function.
    """
    width = get_terminal_size()[0] - 40
    rel_pos = int(float(pos) / total * width)
    bar = ''.join(["=" * rel_pos, "." * (width - rel_pos)])

    # Determine how many digits in total (base 10)
    digits_total = len(str(total))
    fmt_width = "%0" + str(digits_total) + "d"
    fmt = "\r[" + fmt_width + "/" + fmt_width + "][%s] %s"

    progress_stream.write(fmt % (pos, total, bar, msg))


def filename(stream):
    if stream.output["title"] is None:
        data = ensure_unicode(stream.get_urldata())
        if data is None:
            return False
        match = re.search(r"(?i)<title[^>]*>\s*(.*?)\s*</title>", data, re.S)
        if match:
            stream.config.set("output_auto", True)
            title_tag = decode_html_entities(match.group(1))
            stream.output["title"] = filenamify(title_tag)
    return True


def formatname(output, config, extension):
    output["ext"] = extension
    name = config.get("filename")
    for key in output:
        if key == "title" and output[key]:
            name = name.replace("{title}", filenamify(output[key]))
        if key == "season" and output[key]:
            number = "{0:02d}".format(int(output[key]))
            name = name.replace("{season}", number)
        if key == "episode" and output[key]:
            number = "{0:02d}".format(int(output[key]))
            name = name.replace("{episode}", number)
        if key == "episodename" and output[key]:
            name = name.replace("{episodename}", filenamify(output[key]))
        if key == "id" and output[key]:
            name = name.replace("{id}", output[key])
        if key == "service" and output[key]:
            name = name.replace("{service}", output[key])
        if key == "ext" and output[key]:
            name = name.replace("{ext}", output[key])

    # Remove all {text} we cant replace with something
    for item in re.findall("([\.\-](([^\.\-]+\w+)?\{[\w\-]+\}))", name):
        name = name.replace(item[0], "")

    return name


def output(output, config, extension="mp4", mode="wb", **kwargs):
    # subtitlefiles = ["srt", "smi", "tt", "sami", "wrst"]
    print(output)

    name = formatname(output, config, extension)
    if config.get("output") and os.path.isdir(os.path.expanduser(config.get("output"))):
        name = os.path.join(config.get("output"), name)
    elif config.get("path") and os.path.isdir(os.path.expanduser(config.get("path"))):
        name = os.path.join(os.path.expanduser(config.get("output")), name)

    filename, ext = os.path.splitext(name)

    # ext = re.search(r"(\.\w{2,4})$", options.output)
    # if not ext:
    #     options.output = "%s.%s" % (options.output, extension)
    # if options.output_auto and ext:
    #     options.output = "%s.%s" % (options.output, extension)
    # elif extension == "srt" and ext:
    #     options.output = "%s.srt" % options.output[:options.output.rfind(ext.group(1))]
    # if ext and extension == "srt" and ext.group(1).split(".")[-1] in subtitlefiles:
    #    options.output = "%s.srt" % options.output[:options.output.rfind(ext.group(1))]
    logging.info("Outfile: %s", name)
    if os.path.isfile(name):
        logging.warning("File ({}) already exists. Use --force to overwrite".format(name))
        return None
    # if os.path.isfile(name) or \
    #         findexpisode(os.path.dirname(os.path.realpath(name)), options.service, os.path.basename(options.output)):
    #     if extension in subtitlefiles:
    #         if not options.force_subtitle:
    #             if not (options.silent or options.silent_semi):
    #                 logging.warning("File (%s) already exists. Use --force-subtitle to overwrite" % options.output)
    #             return None
    #     else:
    #         if not options.force:
    #             if not (options.silent or options.silent_semi):
    #                 logging.warning("File (%s) already exists. Use --force to overwrite" % options.output)
    #             return None
    file_d = open(name, mode, **kwargs)
    return file_d


def findexpisode(directory, service, name):
    subtitlefiles = ["srt", "smi", "tt", "sami", "wrst"]
    match = re.search(r"-(\w+)-\w+.(\w{2,3})$", name)
    if not match:
        return False

    videoid = match.group(1)
    extension = match.group(2)

    files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
    for i in files:
        match = re.search(r"-(\w+)-\w+.(\w{2,3})$", i)
        if match:
            if service:
                if extension in subtitlefiles:
                    if name.find(service) and match.group(1) == videoid and match.group(2) == extension:
                        return True
                elif match.group(2) not in subtitlefiles and match.group(2) != "m4a":
                    if name.find(service) and match.group(1) == videoid:
                        return True

    return False
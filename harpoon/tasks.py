from harpoon.formatter import MergedOptionStringFormatter
from harpoon.errors import BadOption

from docker.errors import APIError as DockerAPIError
import logging
import os

log = logging.getLogger("harpoon.tasks")

available_tasks = {}
def a_task(func):
    available_tasks[func.__name__] = func
    return func

def determine_image(harpoon, image):
    """Complain if we don't have an image"""
    available = None
    try:
        available = harpoon.imager.images.keys()
    except:
        pass

    if image is None:
        info = {}
        if available:
            info["available"] = available
        raise BadOption("Please use --image to specify an image to run /bin/bash in", **info)

    images = harpoon.imager.images
    if image not in images:
        raise BadOption("No such image", wanted=image, available=images.keys())

    return images, image

def find_missing_env(env):
    """Find any missing environment variables"""
    missing = []
    if isinstance(env, list):
        for thing in env:
            if '=' not in thing:
                if thing not in os.environ:
                    missing.append(thing)

    if missing:
        raise BadOption("Some environment variables aren't in the current environment", missing=missing)

@a_task
def push(harpoon, image=None, **kwargs):
    """Push an image"""
    images, image = determine_image(harpoon, image)
    pushable = dict((image, instance) for image, instance in images.items() if instance.heira_formatted("image_index", default=None))
    if image not in pushable:
        raise BadOption("The chosen image does not have a image_index configuration", wanted=image, available=pushable.keys())
    harpoon.imager.make_image(image)
    pushable[image].push()

@a_task
def make(harpoon, image=None, **kwargs):
    """Just create an image"""
    images, image = determine_image(harpoon, image)
    harpoon.imager.make_image(image)
    print("Created image {0}".format(images[image].image_name))

@a_task
def run_task(harpoon, image=None, command=None, bash=None, env=None, volumes=None, **kwargs):
    """Run specified task in this image"""
    if bash:
        command = "/bin/bash -c '{0}'".format(bash)
    _, image = determine_image(harpoon, image)
    find_missing_env(env)
    harpoon.imager.run(image, command=command, env=env, volumes=volumes)

@a_task
def list_tasks(harpoon, **kwargs):
    """List the available_tasks"""
    print("Available tasks to choose from are:")
    print("---")
    for key, task in sorted(harpoon.find_tasks().items()):
        print("{0}: {1}".format(key, task.description or ""))
    print("---")
    print("Use the --task option to choose one")

@a_task
def delete_untagged(harpoon, **kwargs):
    """Find the untagged images and remove them"""
    images = harpoon.docker_context.images()
    found = False
    for image in images:
        if image["RepoTags"] == ["<none>:<none>"]:
            found = True
            image_id = image["Id"]
            log.info("Deleting untagged image\thash=%s", image_id)
            try:
                harpoon.docker_context.remove_image(image["Id"])
            except DockerAPIError as error:
                log.error("Failed to delete image\thash=%s\terror=%s", image_id, error)

    if not found:
        log.info("Didn't find any untagged images to delete!")


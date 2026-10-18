import pygame

MIN_LAYER_SIZE = (1400, 950)


class LayerCache:
    def __init__(self):
        self.layers = {}

    def _surface(self, name, size, flags):
        cached = self.layers.get(name)
        if cached is None or cached.get_width() < size[0] or cached.get_height() < size[1]:
            cached = pygame.Surface((max(MIN_LAYER_SIZE[0], size[0]), max(MIN_LAYER_SIZE[1], size[1])), *flags)
            self.layers[name] = cached
        return cached.subsurface((0, 0, *size))

    def layer(self, name, size):
        result = self._surface(name, size, (pygame.SRCALPHA,))
        result.set_alpha(255)
        result.fill((0, 0, 0, 0))
        return result

    def canvas(self, size):
        return self._surface('canvas', size, ())

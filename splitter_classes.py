MAX_SPLIT_LEVELS = 256

class Split:
    def __init__(self, start, finish):
        self._start = float(start)
        self._finish = float(finish)
        self._levels = 0
        self._offset = 0
        self._label = None

    def _pointsToLevelMap(self, p):
        points = sorted(list(set(p)))
        span = self.finish - self.start
        scalePoint = lambda x: (x - self.start)/span			
        return {pkey: self.offset + (round(scalePoint(pkey) * self.levels)) for pkey in points}
    
    def _pointsToLevelMapCompressed(self, p):
        points = sorted(list(set(p)))
        pointCount = len(points)
        mapping = {}
        for point_index in range(pointCount):
            mapping[points[point_index]] = self.offset + round((point_index / (pointCount - 1)) * self.levels)
        return mapping			

    def pointsToLevelMap(self, points, compress = False):
        if self.levels == 0:
            return {}
        relevant = [x for x in points if self.contains(x)]
        if compress:
            return self._pointsToLevelMapCompressed(relevant)
        else:
            return self._pointsToLevelMap(relevant)
            
    @property
    def start(self):
        return self._start
    @start.setter
    def start(self, value):
        self._start = value
    
    @property
    def finish(self):
        return self._finish
    @finish.setter
    def finish(self, value):
        self._finish = value
    
    @property
    def levels(self):
        return self._levels
    @levels.setter
    def levels(self, value):
        self._levels = value
        
    @property
    def offset(self):
        return self._offset
    @offset.setter
    def offset(self, value):
        self._offset = value
    
    @property
    def label(self):
        return self._label
    @label.setter
    def label(self, value):
        self._label = value	
    
    def contains(self, value):
        return value >= self.start and value < self.finish

class SplitManager:
    def __init__(self, minDepth, maxDepth):
        self._splits = [Split(minDepth, maxDepth + 0.1)]
        self._splits[0].label = 'Default'
        self._splits[0].levels = MAX_SPLIT_LEVELS
    
    def addSplit(self, point):
        owner = [sp for sp in self._splits if sp.contains(point)]
        if len(owner) != 1:
            print( f"Found too few or too many owners for point {point}:" )
            for o in owner:
                print(f" ** {o}: {o.start} - {o.finish}")
            raise
        owner = owner[0]
        newSplit = Split(point, owner.finish)
        owner.finish = point
        self._splits.append(newSplit)
        self._splits.sort(key = lambda x: x.start)
    
    def removeSplit(self, index):
        if len(self._splits) == 1 or index >= len(self._splits):
            return False
        if index == 0:
            old_start = self._splits[index].start
            self._splits[index+1].start = old_start
            del(self._splits[index])
        else:
            old_endpoint = self._splits[index].finish
            self._splits[index-1].finish = old_endpoint
            del(self._splits[index])
        return True

    def allocateLevels(self, index, levels):
        self._splits[index].levels = levels

    def renameSplit(self, index, label):
        self._splits[index].label = label

    def show(self):
        lines = ['Splits:']
        for index in range(len(self._splits)):
            split = self._splits[index]
            label = split.label if split.label else "Unnamed Split"
            lines.append(f" ** {index:03} - {label} ({split}): {split.start} to {split.finish}, {split.levels} levels")
        return lines

    def totalLevels(self):
        return sum([x.levels for x in self._splits])

    def indexOffsets(self):
        offset = 0
        for split in self._splits:
            split.offset = offset
            offset += split.levels

    def makeMapping(self, points, compress = False):
        tl = self.totalLevels()
        if tl > MAX_SPLIT_LEVELS:
            return (f'Too many levels: {tl}', {})
        self.indexOffsets()
        mapping = {}
        for split in self._splits:
            mapping.update(split.pointsToLevelMap(points, compress = compress))
        return ('Success', mapping)

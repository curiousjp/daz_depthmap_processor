EPSILON = 0.01
MAX_SPLIT_LEVELS = 256

class Split:
    def __init__(self, start, end):
        self._start = float(start)
        self._end = float(end)
        self._levels = 0
        self._flags = {}

    def _pointsToLevelMap(self, p):
        points = sorted(list(set(p)))
        offset = self.getFlag('offset', 0)
        span = self.end - self.start
        scalePoint = lambda x: (x - self.start)/span			
        return {pkey: offset + (round(scalePoint(pkey) * self.levels)) for pkey in points}
    
    def _pointsToLevelMapCompressed(self, p):
        points = sorted(list(set(p)))
        offset = self.getFlag('offset', 0)
        pointCount = len(points)
        mapping = {}
        for point_index in range(pointCount):
            mapping[points[point_index]] = offset + round((point_index / (pointCount - 1)) * self.levels)
        return mapping			

    def pointsToLevelMap(self, points, compress = False):
        if self.levels == 0:
            return {}
        relevant = [x for x in points if self.contains(x)]
        if compress:
            return self._pointsToLevelMapCompressed(relevant)
        else:
            return self._pointsToLevelMap(relevant)

    def setFlag(self, flag, value):
        flag = flag.lower()
        self._flags[flag] = value
    
    def getFlag(self, flag, default = None):
        flag = flag.lower()
        return self._flags.get(flag, default)
    
    def getFlags(self):
        return list(self._flags.keys())

    def contains(self, value):
        return value >= self.start and value < self.end

    def information(self, points = None):
        value = {
            'start': self._start,
            'end': self._end,
            'levels': self._levels,
        }
        for flag, flag_value in self._flags.items():
            value[f'flag: {flag}'] = flag_value
        if points:
            relevant = [x for x in points if self.contains(x)]
            value.update({
                'point_count': len(relevant),
                'point_max': max(relevant),
                'point_min': min(relevant),
                'points': relevant
            })
        return value

    @property
    def start(self):
        return self._start
    @start.setter
    def start(self, value):
        self._start = value
    @property
    def end(self):
        return self._end
    @end.setter
    def end(self, value):
        self._end = value  
    @property
    def levels(self):
        return self._levels
    @levels.setter
    def levels(self, value):
        self._levels = value

class SplitManager:
    def __init__(self, minDepth, maxDepth):
        self._splits = [Split(minDepth, maxDepth + EPSILON)]
        self._splits[0].levels = MAX_SPLIT_LEVELS
        self._splits[0].setFlag('label', 'Default')
    
    def information(self, index, points = None):
        if index < 0 or index >= len(self._splits):
            return (f'Error - index {index} out of range ({len(self._splits)} registered splits)', None)
        return ('Success', self._splits[index].information(points))

    def setFlag(self, index, flag, value):
        if index < 0 or index >= len(self._splits):
            return (f'Error - index {index} out of range ({len(self._splits)} registered splits)', None)
        self._splits[index].setFlag(flag, value)
        return ('Success', self._splits[index].getFlag(flag))
    
    def getFlag(self, index, flag):
        if index < 0 or index >= len(self._splits):
            return (f'Error - index {index} out of range ({len(self._splits)} registered splits)', None)
        return ('Success', self._splits[index].getFlag(flag))
    
    def getFlags(self, index):
        if index < 0 or index >= len(self._splits):
            return (f'Error - index {index} out of range ({len(self._splits)} registered splits)', None)
        return ('Success', self._splits[index].getFlags())

    def countSplits(self):
        return len(self._splits)

    def addSplit(self, depth):
        # first, determine which split currently holds this depth
        owners = [sp for sp in self._splits if sp.contains(depth)]
        if len(owners) == 0:
            return ('Error - this point is outside the range of this depth map.', None)
        if len(owners) > 1:
            return ('Error - this point is somehow contained within two splits - this should never happen! You may need to restart.', None)
        owner = owners[0]
        newSplit = Split(depth, owner.end)
        owner.end = depth
        self._splits.append(newSplit)
        self._splits.sort(key = lambda x: x.start)
        return ('Success', newSplit)
    
    def moveSplit(self, fromDepth, toDepth):
        # is there a split that starts or ends on the desired depth? (it won't be both)
        start_candidates = [x for x in self._splits if x.start == fromDepth]
        end_candidates = [x for x in self._splits if x.end == fromDepth]

        # we are going to move the starting position of an identified split
        if len(start_candidates) == 1:
            split_index = self._splits.index(start_candidates[0])
            if split_index == 0:
                return (f'Error - will not move the start of the first split as this would cause the SplitManager to not cover the entire depthmap. Add a split at your proposed position instead.', False)
            if toDepth <= self._splits[split_index - 1].start:
                return (f'Error - will not move the start of split {split_index} past the beginning of split {split_index - 1} - are you trying to delete a split?', False)
            if toDepth >= self._splits[split_index].end:
                return (f'Error - will not move the start of split {split_index} past its own ending - are you trying to delete a split?', False)
            self._splits[split_index].start = toDepth
            self._splits[split_index - 1].end = toDepth
            return ('Success', True)
        # we are going to move the end position of an identified split
        elif len(end_candidates) == 1:
            split_index = self._splits.index(end_candidates[0])
            if split_index == len(self._splits) - 1:
                return (f'Error - will not move the end of the last split as this would cause the SplitManager to not cover the entire depthmap. Add a split at your proposed position instead.', False)
            if toDepth <= self._splits[split_index].start:
                return (f'Error - will not move the end of split {split_index} past its own beginning - are you trying to delete a split?', False)
            if toDepth >= self._splits[split_index + 1].end:
                return (f'Error - will not move the end of split {split_index} past the end of split {split_index + 1} - are you trying to delete a split?', False)
            self._splits[split_index].end = toDepth
            self._splits[split_index + 1].start = toDepth
            return ('Success', True)
        else:
            return (f'Error - could not identify {fromDepth} as uniquely pointing to the start or end of any split.', None)

    def removeSplit(self, index):
        if len(self._splits) == 1:
            return ('Error - you cannot remove a split from a manager with only one split.', False)      
        if index < 0 or index >= len(self._splits):
            return (f'Error - index of {index} is out of range.', False)
        
        if index == 0:
            self._splits[1].start = self._splits[0].start
            del(self._splits[0])
            return ('Success - Removed split 0 and expanded split 1 backwards.', True)
        else:
            self._splits[index - 1].end = self._splits[index].end
            del(self._splits[index])
            return (f'Success - Removed split {index} and expanded split {index - 1} forwards.', True)

    def allocateLevels(self, index, levels):
        self._splits[index].levels = levels
        return self.totalLevels()
    
    def totalLevels(self):
        total = sum([x.levels for x in self._splits])
        return (f'{total} levels allocated.', (total <= MAX_SPLIT_LEVELS))

    def findSplitForDepth(self, depth):
        for sp in self._splits:
            if sp.contains(depth):
                return ('Success', sp)
        return (f'Unable to locate a split containing depth {depth}.', None)

    def indexOffsets(self):
        offset = 0
        for split in self._splits:
            split.setFlag('offset', offset)
            offset += split.levels

    def makeMapping(self, points, compress = False):
        message, safe_levels = self.totalLevels()
        if safe_levels == False:
            return (f'Failure to map: {message}', False)
        self.indexOffsets()
        mapping = {}
        for split in self._splits:
            mapping.update(split.pointsToLevelMap(points, compress = compress))
        return ('Success', mapping)

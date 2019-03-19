from arcgis.gis import GIS
from arcgis._impl.common._mixins import PropertyMap
import collections
import json

def _lazy_property(fn):
    '''Decorator that makes a property lazy-evaluated.
    '''
    # http://stevenloria.com/lazy-evaluated-properties-in-python/
    attr_name = '_lazy_' + fn.__name__

    @property
    def _lazy_property(self):
        if not hasattr(self, attr_name):
            setattr(self, attr_name, fn(self))
        return getattr(self, attr_name)
    return _lazy_property

class Hub(object):
    """Entry point. Acceessing an individual hub and its components"""
    
    def __init__(self, url, username=None, password=None):
        self.url = url
        self._username = username
        self._password = password
        self.org = GIS(self.url, self._username, self._password)
        try:
            self._org_id = self.org.properties.id
        except AttributeError:
            return "Invalid Hub"
            sys.exit(0)
            
    @property
    def enterprise_orgId(self):
        '''Get the enterprise org id for this hub'''
        try:
            return self.org.properties.portalProperties.hub.settings.enterpriseOrg.orgId
        except AttributeError: 
            return self._org_id
            
    @property
    def community_orgId(self):
        '''Get the community org id for this hub'''
        try:
            return self.org.properties.portalProperties.hub.settings.communityOrg.orgId
        except AttributeError:
            return self._org_id
  
    @property
    def enterprise_orgUrl(self):
        '''Get the enterprise org url for this hub'''
        try:
            return self.org.properties.portalProperties.hub.settings.enterpriseOrg.portalHostname
        except AttributeError:
            return self.org.url
        
    @property
    def community_orgUrl(self):
        '''Get the community org url for this hub'''
        try:
            return self.org.properties.portalProperties.hub.settings.communityOrg.portalHostname
        except AttributeError:
            return self.org.url
    
    @_lazy_property
    def initiatives(self):
        return InitiativeManager(self)
    
    @_lazy_property
    def events(self):
        return EventManager(self)
    
class Initiative(collections.OrderedDict):
    """Represents an initiative"""
    
    def __init__(self, org, initiativeItem):
        '''Constructs an empty Initiative object'''
        if 'hubInitiative' not in initiativeItem.typeKeywords:
            raise TypeError("Item is not a valid initiative.")
        self.item = initiativeItem
        self._org = org
        self._initiativedict = self.item.get_data()
        pmap = PropertyMap(self._initiativedict)
        self.definition = pmap
            
    def __repr__(self):
        return '<%s title:"%s" owner:%s>' % (type(self).__name__, self.title, self.owner)
       
    @property
    def itemId(self):
        return self.item.id
    
    @property
    def title(self):
        return self.item.title
    
    @property
    def owner(self):
        return self.item.owner
    
    @_lazy_property
    def indicators(self):
        return IndicatorManager(self.item)
    
    def delete(self, force=False, dry_run=False):
        '''Deletes an initiative''' 
        if self.item is not None:
            return self.item.delete(force, dry_run)
    
    def update(self, initiative_properties=None, data=None, thumbnail=None, metadata=None):
        '''Update an initiative'''
        if initiative_properties:
            return self.item.update(initiative_properties, data, thumbnail, metadata)          
    
class InitiativeManager(object):
    """Helper class for managing initiatives within a Hub"""
    
    def __init__(self, hub, initiative=None):
        self._org = hub.org
        if initiative:
            self._initiative = initiative
          
    def add(self, initiative_properties, data=None, thumbnail=None, metadata=None, owner=None, folder=None):
        '''Adding an initiative'''
        try:
            if 'hubInitiaitve' not in initiative_properties['typekeywords']:
                initiative_properties['typekeywords'].append("hubInitiative")
        except:
                initiative_properties['typekeywords'] = "hubInitiative"
        item = self._org.content.add(initiative_properties, data, thumbnail, metadata, owner, folder)
        return Initiative(self._org, item)
    
    def get(self, initiative_id):
        '''Fetch initiative for given initiative id'''
        initiativeItem = self._org.content.get(initiative_id)
        if 'hubInitiative' in initiativeItem.typeKeywords:
            return Initiative(self._org, initiativeItem)
        else:
            raise TypeError("Item is not a valid initiative or is inaccessible.")
    
    def search(self, initiative_id=None, title=None, owner=None, created=None, modified=None, tags=None):
        '''Search for initiative'''
        initiativelist = []
        query = 'typekeywords:hubInitiative'
        if initiative_id!=None:
            query += ' AND id:'+initiative_id
        if title!=None:
            query += ' AND title:'+title
        if owner!=None:
            query += ' AND owner:'+owner
        if created!=None:
            query += ' AND created:'+created
        if modified!=None:
            query += ' AND modified:'+modified
        if tags!=None:
            query += ' AND tags:'+tags
        items = self._org.content.search(query=query, max_items=5000)
        for item in items:
            initiativelist.append(Initiative(self._org, item))
        return initiativelist
        
class Indicator(collections.OrderedDict):
    """Represents an indicator within an initiative"""
    
    def __init__(self, initiativeItem, indicatorObject):
        '''Constructs an empty Indicator object'''
        self._initiativeItem = initiativeItem
        self._initiativedata = self._initiativeItem.get_data()
        self._indicatordict = indicatorObject
        pmap = PropertyMap(self._indicatordict)
        self.definition = pmap
            
    def __repr__(self):
        return '<%s id:"%s" optional:%s>' % (type(self).__name__, self.indicatorId, self.optional)
       
    @property
    def indicatorId(self):
        return self._indicatordict['id']
    
    @property
    def indicatorType(self):
        return self._indicatordict['type']
    
    @property
    def optional(self):
        return self._indicatordict['optional']
    
    @property
    def url(self):
        try:
            return self._indicatordict['source']['url']
        except:
            return 'Url not available for this indicator'
        
    @property
    def name(self):
        try:
            return self._indicatordict['source']['url']
        except:
            return 'Name not available for this indicator'
        
    @property
    def itemId(self):
        try:
            return self._indicatordict['source']['itemId']
        except:
            return 'Item Id not available for this indicator'
        
    @property
    def mappings(self):
        try:
            return self._indicatordict['source']['mappings']
        except:
            return 'Attribute mapping not available for this indicator'
    
    def delete(self):
        '''Deletes an indicator from the initiative'''
        if self._indicatordict is not None:
            _indicator_id = self._indicatordict['id']
            self._initiativedata['indicators'] = list(filter(lambda indicator: indicator.get('id')!=_indicator_id, self._initiativedata['indicators']))
            _new_initiativedata = json.dumps(self._initiativedata)
            return self._initiativeItem.update(item_properties={'text': _new_initiativedata})
     
    def get_data(self):
        '''Retrieves the data associated with this indicator'''
        return self.definition
    
    def update(self, indicator_properties=None):
        '''Updates specified properties of an indicator'''
        try:
            _indicatorId = indicator_properties['id']
        except:
            return 'Indicator properties must include id of indicator'
        if indicator_properties is not None:
            self._initiativedata['indicators'] = [indicator_properties if indicator['id']==_indicatorId else indicator for indicator in self._initiativedata['indicators']]
            _new_initiativedata = json.dumps(self._initiativedata)
            status = self._initiativeItem.update(item_properties={'text': _new_initiativedata})      
            if status:
                self.definition = PropertyMap(indicator_properties)
                return status
    
class IndicatorManager(object):
    """Helper class for managing indicators within an initiative"""
    def __init__(self, initiativeItem):
        self._initiativeItem = initiativeItem
        self._initiativedata = self._initiativeItem.get_data()
        self._indicators = self._initiativedata['indicators']
        
    def add(self, indicator_properties):
        '''Adds a new indicator to given initiative'''
        self._initiativedata['indicators'].append(indicator_properties)
        _new_initiativedata = json.dumps(self._initiativedata)
        self._initiativeItem.update(item_properties={'text': _new_initiativedata})
        return Indicator(self._initiativeItem, indicator_properties)
    
    def get(self, indicator_id):
        '''Fetch initiative for given initiative id'''
        for indicator in self._indicators:
            if indicator['id']==indicator_id:
                return Indicator(self._initiativeItem, indicator)
        return None
    
    def search(self, indicator_id=None, url=None, itemId=None, name=None):
        '''Search for indicator'''
        _indicators = []
        indicatorlist = []
        for indicator in self._indicators:
            _indicators.append(indicator)
        if indicator_id!=None:
            _indicators = [indicator for indicator in _indicators if indicator['id']==indicator_id]
        if url!=None:
            _indicators = [indicator for indicator in _indicators if indicator['source']['url']==url]
        if itemId!=None:
            _indicators = [indicator for indicator in _indicators if indicator['source']['itemId']==itemId]
        if name!=None:
            _indicators = [indicator for indicator in _indicators if indicator['source']['name']==name]
        for indicator in _indicators:
            indicatorlist.append(Indicator(self._initiativeItem, indicator))
        return indicatorlist
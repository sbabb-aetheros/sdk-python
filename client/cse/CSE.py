#!/usr/bin/env python

import json, random

from client.ae.AE import AE
from client.onem2m.OneM2MResource import OneM2MResource
from client.onem2m.OneM2MPrimitive import OneM2MPrimitive
from client.onem2m.http.OneM2MRequest import OneM2MRequest
from client.onem2m.OneM2MOperation import OneM2MOperation
from client.onem2m.resource.ContentInstance import ContentInstance as ContentInstance
from client.onem2m.resource.Subscription import Subscription
from client.exceptions.InvalidArgumentException import InvalidArgumentException

class CSE():

    def __init__(self, host, port, rsc):
        """Constructor
        
        Args:
            host (str): CSE host
            port (int): CSE port
            rsc (str): Base resource
        """
        self.transport_protocol = 'http'
        self.host = host
        self.port = port
        self.ae = None 
        self.rsc = rsc

    def register_ae(self, ae):
        """Synchronously register an AE with a CSE.
        
        Args:
            ae (AE): The AE to register.

        Returns:
            OneM2MResponse: The request response.

        Raises:
            InvalidArgumentException: If the argument is not an AE or a dict containing AE attributes.
        """
        if isinstance(ae, AE) is False:
            raise InvalidArgumentException('AE registration expects an instance AE.')

        # Host and resource.
        to = '{}://{}:{}/PN_CSE?rcn=0'.format(self.transport_protocol, self.host, self.port)

        # op is not required as it is implied by the function that the params will be passed to.
        params = {
            OneM2MPrimitive.M2M_PARAM_OPERATION: 'Create', 
            OneM2MPrimitive.M2M_PARAM_TO: to,
            OneM2MPrimitive.M2M_PARAM_FROM: ae.aei
        }

        # Create a request object
        oneM2MRequest = OneM2MRequest()

        # Returns a OneM2MResponse object.  Handle any response code logic here.
        oneM2MResponse = oneM2MRequest.create(to, params, ae)

        # Return the AE instance or None if registration failed.
        # @todo return error msg or object with error msg.
        if oneM2MResponse.rsc == OneM2MPrimitive.M2M_RSC_CREATED:
            self.ae = AE(oneM2MResponse.pc)

        return oneM2MResponse

    def discover_containers(self):
        """ Synchronously discover containers registered with the CSE.
        
        Returns:
            list: A list of container resource URIs or None.

        Raises:
            InvalidArgumentException: If the argument is not an AE.
        """
        # note: fu (filter usage) parameter required for resource discovery
        to = '{}://{}:{}/{}'.format(self.transport_protocol, self.host, self.port, self.rsc)

        # Create a request object
        oneM2MRequest = OneM2MRequest(to)

        oneM2MRequest.set_param(OneM2MRequest.M2M_PARAM_FILTER_USAGE, 1)
        oneM2MRequest.set_param(OneM2MRequest.M2M_PARAM_FROM, self.ae.ri)
        oneM2MRequest.set_param(OneM2MRequest.M2M_PARAM_RESOURCE_TYPE, OneM2MResource.M2M_TYPE_CONTAINER) 

        # Returns a OneM2MResponse object.  Handle any response code logic here.
        oneM2MResponse = oneM2MRequest.retrieve()

        # Deserialize the primitive container.
        pc = json.loads(oneM2MResponse.pc)

        if 'uril' in pc.keys():
            return pc['uril']

        # @todo raise an exception indicating the expected response object was not receieved.
        return None

    # @todo add possible rcn values to OneM2MResource class.
    def create_content_instance(self, uri):
        """Create a content instance of a container resource.

        Args:
            uri: URI of a container resource.

        Returns:
            OneM2MResponse: The request response.
        """

        # Strip leading '/'
        uri = uri[1:] if uri[0] is '/' else uri

        to = '{}://{}:{}/{}?rcn=3'.format(self.transport_protocol, self.host, self.port, uri)
        params = {
            OneM2MPrimitive.M2M_PARAM_FROM: self.ae.ri, # resource id.
            OneM2MRequest.M2M_PARAM_RESULT_CONTENT: 1, # @todo add as function arg.
            OneM2MPrimitive.X_M2M_RTV: 1
        }
        
        content_instance = ContentInstance(
            {
                'con': 'default content'
            }
        )

        oneM2MRequest = OneM2MRequest()

        oneM2MResponse = oneM2MRequest.create(to, params, content_instance)

        return oneM2MResponse

    def retrieve_content_instance(self, uri, rcn=7):
        """Retrieves the latest content instance of a container resource.

        Args:
            uri: URI of a resource.

        Returns:
            OneM2MResponse: The request response.
        """
        
        # Remove leading slash
        uri = uri[1:] if uri[0] is '/' else uri
        to = '{}://{}:{}/{}?rcn=3'.format(self.transport_protocol, self.host, self.port, uri)

        params = {
            OneM2MPrimitive.M2M_PARAM_FROM: self.ae.ri, 
            OneM2MRequest.M2M_PARAM_RESULT_CONTENT: ''
        }

        oneM2MRequest = OneM2MRequest(to, params)

        oneM2MResponse = oneM2MRequest.retrieve()

        return oneM2MResponse

    def create_subscription(self, rsc, notification_uri):
        """ Create a subscription to a resource.

        Args:
            uri: URI of a resource.

        Returns:
            OneM2MResponse: The request response.
        """

        rsc = rsc[1:] if rsc[0] is '/' else rsc
        to = '{}://{}:{}/{}'.format(self.transport_protocol, self.host, self.port, rsc)
        
        params = {
            OneM2MPrimitive.M2M_PARAM_FROM: self.ae.ri, 
        }

        content = Subscription({'enc': { 'net': [3], 'ty': 4 }, 'nct': 1, 'nu': [notification_uri]})

        oneM2MRequest = OneM2MRequest()

        oneM2MResponse = oneM2MRequest.create(to, params, content)

        return oneM2MResponse

    # @note: not really working.  'la' virtual resource never returns the latest content instance.
    def retrieve_latest_content_instance(self, uri):
        """Retrieve the latest content instance of a container.

        Args:
            uri: The container resource URI. 

        Returns:
            An instance of ContentInstance or None if no content instance was found.

        Raises:
            ...
        """

        # Remove leading slash
        uri = uri[1:] if uri[0] is '/' else uri
        to = '{}://{}:{}/{}/la'.format(self.transport_protocol, self.host, self.port, uri)

        params = {
            OneM2MPrimitive.M2M_PARAM_FROM: self.ae.ri, 
        }

        oneM2MRequest = OneM2MRequest(to, params)

        oneM2MResponse = oneM2MRequest.retrieve()

        # How do you want to handle responses?
        if oneM2MResponse.uri == OneM2MPrimitive.M2M_RSC_OK:
            return ContentInstance(json.loads(oneM2MResponse.pc)['cin'])
        else:
            return None

    def retrieve_resource(self, uri, rcn=OneM2MRequest.M2M_RCN_HIERARCHICAL_ADDRESS):
        """ Synchronous retrieve resource request.
        
        Args:
            uri: The URI of the resource to retrieve.
            rcn: 

        Returns:
            A OneM2MResource object.
        """

        # Remove leading '/'
        uri = uri[1:] if uri[0] is '/' else uri

        to = '{}://{}:{}/{}?rcn={}'.format(self.transport_protocol, self.host, self.port, uri, rcn)

        params = {
            OneM2MPrimitive.M2M_PARAM_FROM:  self.ae.ri,
        }

        oneM2MRequest = OneM2MRequest(to, params)

        oneM2MReponse = oneM2MRequest.retrieve()

        return oneM2MReponse

    def update_resource(self, uri, short_name, key, value):
        """ Update a resource.
        
        Args:
            uri: The URI of the resource to retrieve.
            short_name:
            key:
            value: 

        Returns:
            OneM2MResponse: The request response.
        """

        uri = uri[1:] if uri[0] is '/' else uri
        to = '{}://{}:{}/{}'.format(self.transport_protocol, self.host, self.port, uri)
        
        params = {
            OneM2MPrimitive.M2M_PARAM_FROM: self.ae.ri
        }

        oneM2MRequest = OneM2MRequest()

        oneM2MResponse = oneM2MRequest.update(to, params, short_name, key, value)

        return oneM2MResponse

    def delete_ae(self):
        """ Delete ae.
        
        Returns:
            OneM2MResponse: The request response.
        """
        # Host and resource.
        to = '{}://{}:{}/PN_CSE/{}'.format(self.transport_protocol, self.host, self.port, self.ae.ri)

        # op is not required as it is implied by the function that the params will be passed to.
        params = {
            OneM2MPrimitive.M2M_PARAM_OPERATION: 'Delete', 
            OneM2MPrimitive.M2M_PARAM_TO: 'http://{}:{}/PN_CSE/{}'.format(self.host, self.port, self.ae.ri),
            OneM2MPrimitive.M2M_PARAM_FROM:  self.ae.ri
        }

        # Create a request object
        oneM2MRequest = OneM2MRequest()

        # Returns a OneM2MResponse object.  Handle any response code logic here.
        oneM2MResponse = oneM2MRequest.delete(to, params)

        return oneM2MResponse
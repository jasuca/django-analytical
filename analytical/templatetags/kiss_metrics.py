"""
KISSmetrics template tags.
"""

from __future__ import absolute_import

import re

from django.template import Library, Node, TemplateSyntaxError
from django.utils import simplejson

from analytical.utils import is_internal_ip, disable_html, get_identity, \
        get_required_setting, on_debug_mode


API_KEY_RE = re.compile(r'^[0-9a-f]{40}$')
TRACKING_CODE = """
    <script type="text/javascript">
      var _kmq = _kmq || [];
      %(commands)s
      function _kms(u){
        setTimeout(function(){
          var s = document.createElement('script');
          s.type = 'text/javascript';
          s.async = true;
          s.src = u;
          var f = document.getElementsByTagName('script')[0];
          f.parentNode.insertBefore(s, f);
        }, 1);
      }
      _kms('//i.kissmetrics.com/i.js');
      _kms('//doug1izaerwt3.cloudfront.net/%(api_key)s.1.js');
    </script>
"""
IDENTIFY_CODE = "_kmq.push(['identify', '%s']);"
EVENT_CODE = "_kmq.push(['record', '%(name)s', %(properties)s]);"
PROPERTY_CODE = "_kmq.push(['set', %(properties)s]);"

EVENT_CONTEXT_KEY = 'kiss_metrics_event'
PROPERTY_CONTEXT_KEY = 'kiss_metrics_properties'

register = Library()


@register.tag
def kiss_metrics(parser, token):
    """
    KISSinsights tracking template tag.

    Renders Javascript code to track page visits.  You must supply
    your KISSmetrics API key in the ``KISS_METRICS_API_KEY``
    setting.
    """
    bits = token.split_contents()
    if len(bits) > 1:
        raise TemplateSyntaxError("'%s' takes no arguments" % bits[0])
    return KissMetricsNode()


class KissMetricsNode(Node):
    def __init__(self):
        self.api_key = get_required_setting('KISS_METRICS_API_KEY',
                API_KEY_RE,
                "must be a string containing a 40-digit hexadecimal number")

    def render(self, context):
        commands = []
        identity = get_identity(context, 'kiss_metrics')
        
        if identity is not None:
            commands.append(IDENTIFY_CODE % identity)
        try:
            
            if len(context[EVENT_CONTEXT_KEY])>=0 and type(context[EVENT_CONTEXT_KEY][0])==type(""):
                #old format
                name, properties = context[EVENT_CONTEXT_KEY]
                commands.append(EVENT_CODE % {'name': name,
                        'properties': simplejson.dumps(properties)})
            else:
                #new format
                for name, properties in context[EVENT_CONTEXT_KEY]:
                    commands.append(EVENT_CODE % {'name': name,
                        'properties': simplejson.dumps(properties)})
        except KeyError:
            pass
        try:
            properties = context[PROPERTY_CONTEXT_KEY]
            commands.append(PROPERTY_CODE % {
                    'properties': simplejson.dumps(properties)})
        except KeyError:
            pass
        html = TRACKING_CODE % {'api_key': self.api_key,
                'commands': " ".join(commands)}
        if is_internal_ip(context, 'KISS_METRICS') or on_debug_mode():
            html = disable_html(html, 'KISSmetrics')
        return html


def contribute_to_analytical(add_node):
    KissMetricsNode()  # ensure properly configured
    add_node('head_top', KissMetricsNode)

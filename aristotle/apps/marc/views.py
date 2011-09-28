"""
  views.py -- Views for MARC record manipulation
"""
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Copyright: 2011 Colorado College
__author__ = 'Jeremy Nelson'

from django.views.generic.simple import direct_to_template
from django.shortcuts import render_to_response
from django.http import Http404,HttpResponseRedirect
from django.template import RequestContext

# Imports Bots
from bots.awbots import AmericanWestBot
from bots.eccobots import ECCOBot
from bots.galebots import GVRLBot
from bots.gutenbergbots import ProjectGutenbergBot


def default(request):
    """Default view for MARC utilities Django application
    """
    active_bots = [AmericanWestBot,ECCOBot,GVRLBot,ProjectGutenbergBot]
    return direct_to_template(request,
                              'marc/index.html',
                              {'workflows':active_bots})

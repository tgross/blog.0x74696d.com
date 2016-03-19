---
layout: page
title: Community

---

Philly has a great tech scene. I regularly attend the Philly DevOps group, I make occasional appearances at PhillyDB and the Python group PhillyPUG, and I try to get to some of the great annual events in Philadelphia like Redsnake and BarCamp.  I've been the sometimes host of the AWS NYC meetup and was the lead organizer for PhillyPUG for a highly chaotic year or so. Feel free to find me at one of these events and tell me how much my blog sucks. Or receive questionable advice about your deployment process, software infrastructure, or startup idea for the low-low price of having a beer or a cup of coffee with me. I occasionally get it into my head to stand up and talk in front of other people, and some of those talks will make their way into this blog in the future.

## Talks, podcasts, and workshops

<ul class="listing">
{% for event in site.data.events %}
<li><i>
  {%if event.link %}<a href="{{ event.link }}">{{ event.title }}</a>{% else %}{{ event.title }}{% endif %}</i>
  <span>
  {%if event.where-link %}<a href="{{ event.where-link }}">{{ event.where }}</a>{% else %}{{ event.where }}{% endif %} | {{ event.when }}
  </span>
</li>
{% endfor %}
</ul>
<br/>

Behold some of my very small contributions to the world below, and realize that you should definitely start working on some open source projects if you aren't already.  I'd like to start contributing to some larger or more important projects, so stay tuned here or in future blog postings to see what kind of comically-bad PRs I send the way of your favorite FOSS project.

## Open source contributions

<ul class="listing">
{% for c in site.data.contrib %}
<li><a href="{{ c.link }}">{{ c.title }}</a><span>{{ c.what }}</span></li>
{% endfor %}
</ul>

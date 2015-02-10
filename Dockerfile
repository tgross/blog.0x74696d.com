FROM ruby:2.1

RUN apt-get update && apt-get install -y node python-pygments && apt-get clean

ADD Gemfile Gemfile
RUN bundle install

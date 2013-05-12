tgross.github.io
--------------

This is the repo for my Github Pages-hosted blog, served on [0x74696d.com](http://0x74696d.com).

## License

This Jekyll project is a fork from [Up](http://github.com/caarlos0/up). The code of this blog and all code content is [MIT](https://github.com/tgross/tgross.github.io/blob/master/LICENSE) licensed, except where a given piece of code is attributed to another author and has a more restrictive license.
The original written prose and images in this repo are licensed under [Creative Common Attribution 3.0 Unported License](http://creativecommons.org/licenses/by-sa/3.0/deed.en_US).

It should be easy to fork and modify this repo if you want, but it's going to be chock full of my personal idiosyncrasies.  You can follow the installation directions below but I'd really encourage you to just to use Up(http://github.com/caarlos0/up) instead.


## Installation

- Fork this repository
- Rename it to `YOUR-USER.github.com`
- Clone it: `git clone https://github.com/YOUR-USER/YOUR-USER.github.com`
- Run the bundler to get the dependencies: `bundle`
- On OS X, installing rmagick may fail.  For Snow Leopard, I had to do the following using `brew`:
    brew update
    brew install imagemagick
    export PKG_CONFIG_PATH=/usr/local/Cellar/imagemagick/6.8.0-10/lib/pkgconfig/:$PKG_CONFIG_PATH
    C_INCLUDE_PATH=/usr/local/Cellar/imagemagick/6.8.0-10/include/ImageMagick/ gem install rmagick

Run the jekyll server with `rake preview`.
You should have a server up and running locally at <http://localhost:4000>.


## Customization

Next you'll want to change a few things. The list of files you may want to
change is the following:

- [_config.yml](https://github.com/tgross/tgross.github.io/blob/gh-pages/_config.yml): Put
your config there, almost everything will be up and running.
- [me.html](https://github.com/tgross/tgross.github.io/blob/gh-pages/me.html): Your about page.
- [CNAME](https://github.com/tgross/tgross.github.io/blob/gh-pages/CNAME): To use a custom domain name on Github pages, change this to your domain.


### Update `favicon` and `apple-precomposed` icons based on gravatar

First, be sure you have the author email configured in `_config.yml`,
then, just run: `rake icons`

The script will generate your email hash and get your gravatar, then, using
RMagick, it will create all needed icons.


## Deployment

You should deploy with [GitHub Pages](http://pages.github.com)- it's just
easier.

All you should have to do is to rename your repository on GitHub to be
`username.github.com`. Since everything is on the `gh-pages` branch, you
should be able to see your new site at <http://username.github.com>.

import sys
sys.path.insert(0,".")
from twisted.application import service, internet
from twisted.internet.defer import Deferred
from nevow import appserver, inevow, loaders, rend, compy, url, tags as T, stan
from formless import annotate, webform, iformless

from docutils.core import publish_string

import pgasync
WIKI_DB_ARGS = {"dbname":"wiki","user":"wiki","password":"wiki"}

import re
wikipage_re = re.compile("([A-Z][a-z]+[a-z0-9]*[A-Z]+\w+)",re.MULTILINE)

pool = pgasync.ConnectionPool("pgasync",**WIKI_DB_ARGS)

def format(text):
	html = publish_string(text, writer_name = 'html')
	frag = html[html.find('<body>')+6:html.find('</body>')].strip()

	return re.sub(wikipage_re,r'<a href="\1">\1</a>',frag)

class IWikiContent(compy.Interface): pass
class IPageTitle(compy.Interface): pass

class IWikiForm(annotate.TypedInterface):
	def updateWiki(self,ctx=annotate.Context(),text=annotate.Text(), new=annotate.String(hidden=True)):
		pass

	updateWiki = annotate.autocallable(updateWiki)

class WikiEdit(rend.Page):
	__implements__ = IWikiForm, rend.Page.__implements__

	def locateChild(self,ctx,segments):
		if len(segments) > 1:
			return rend.Page.locateChild(self,ctx,segments[1:])
		return self,()

	def beforeRender(self, ctx):
		formDefs = iformless.IFormDefaults(ctx).getAllDefaults('updateWiki')
		content = IWikiContent(ctx)
		formDefs['new'] = "0"
		if content:
			formDefs['text'] = stan.xml(content)
		else:
			formDefs['new'] = "1"

	def updateWiki(self, ctx, text, new):
		d = Deferred()
		connection = pool.connect()
		cur = connection.cursor()
		
		if new == "0":
			cur.execute("UPDATE pages SET contents = %(contents)s WHERE name = %(name)s",
				{"name" : IPageTitle(ctx),"contents" : text})
		else:
			cur.execute("INSERT INTO pages VALUES (%(name)s , %(contents)s)",
				{"name" : IPageTitle(ctx),"contents" : text})

		def sendToContent(dc,d):
			request = ctx.locate(inevow.IRequest)
			request.setComponent(iformless.IRedirectAfterPost,"/%s" % IPageTitle(ctx))
			d.callback(None)

		connection.commit().addCallback(sendToContent,d)
		cur.release()

		return d

	def title(self, ctx, data):
		return IPageTitle(ctx)

	docFactory = loaders.stan([T.html[T.head[T.title["Wiki: ",title, " (edit)"]],
					T.body[T.span(_class="pageName")["Editing: ",title],webform.renderForms()]]])

wikiEdit = WikiEdit()
	
class Wiki(rend.Page):
	def locateChild(self,ctx,segments):
		if segments == ('favicon.ico',):
			return rend.NotFound

		if segments == ('',):
			segments = ('FrontPage',)

		def finish(rows,cur,d,segments):
			if cur.rowcount:
				ctx.remember(rows[0][0],IWikiContent)
			else:
				ctx.remember(None,IWikiContent)

			if len(segments) > 1:
				d.callback((wikiEdit,segments[1:]))
			else:
				d.callback((self,()))

		page = segments[0]
		ctx.remember(page,IPageTitle)

		d = Deferred()

		cur = pool.connect().cursor()
		cur.exFetch("SELECT contents FROM pages WHERE name = %(name)s",{"name" : page}
		).addCallback(finish,cur,d,segments)
		cur.release()
		
		return d

	def toolbar(self,ctx,data):
		content = ctx.locate(IWikiContent)
		return T.div(id="toolbar")[
			T.a(href=[IPageTitle(ctx),"/edit"],_class="toolbarLink")[
				content and "[Edit]" or "[Create]"
				]
			]

	def pageContent(self,ctx,data):
		content = ctx.locate(IWikiContent)
		return T.div(style="margin:4px;")[
			content and 
				stan.xml(format(content)) or
				"This page does not yet exist."
			]

	def title(self,ctx,data):
		return IPageTitle(ctx)

	docFactory = loaders.stan([T.html[T.head[T.title["Wiki: ",title]],
					T.body[T.span(_class="pageName")[title],toolbar,T.hr(),pageContent]]])

class ErrorPage(rend.Page):
	def error(self,ctx,data):
		return data

	docFactory = loaders.stan([T.html[T.head[T.title["Database Error"]],
					T.body[T.h1["Database Error"],T.p[error]]]])

application = service.Application("wiki")
internet.TCPServer(
    8080, 
    appserver.NevowSite(
        Wiki()
    )
).setServiceParent(application)

# -*- encoding: utf-8 -*-
import sublime, sublime_plugin
from StringIO import StringIO
import xml.parsers.expat

ignore_data = ["外祖","統首","本","第","曾祖","戶","主","居","父","母","祖","年"]

class HojukChecker: # xsd가 지원되지 않기 때문에 하드코딩
  parser_ = None
  element_stack_ = [("root",[])]
  entered_ = 0
  errors_ = []
  warnings_ = []

  def __init__(self, parser):
    parser.StartElementHandler = self.start_element
    parser.EndElementHandler  = self.end_element
    parser.CharacterDataHandler   = self.char_data
    self.parser_ = parser

  def start_element(self, name, attrs):
    par_name, par_list = self.element_stack_[-1]
    if name == u'사람': # 사람은 중복으로 존재가능 - 예외
      pass
    else:
      if name in par_list:
        self.errors_.append((self.parser_.CurrentLineNumber - 1, self.parser_.CurrentColumnNumber, name))
      else:
        par_list.append(name)
    self.element_stack_.append( (name,[]) )

  def end_element(self, name):
    self.element_stack_.pop()

  def char_data(self, data):
    global ignore_data
    stripped = str.strip(data.encode('utf-8'))
    if stripped in ignore_data:
      return
    if len(stripped) > 0:
      par_name, par_list = self.element_stack_[-1]
      if par_name == u'사람' or par_name == u'문서':
        self.warnings_.append((self.parser_.CurrentLineNumber - 1, self.parser_.CurrentColumnNumber, data))

class HojukCheckCommand(sublime_plugin.TextCommand):
  checker_ = None

  def run(self, edit, target):
    global untagged

    if self.checker_ is None:
      try:
        raw = self.view.substr(sublime.Region(0, self.view.size())).encode('utf-8')
      except Exception as e: 
        sublime.error_message("UTF-8 문서가 아닙니다")
        return

      p = xml.parsers.expat.ParserCreate()
      self.checker_ = HojukChecker(p)
      try:
        p.Parse(raw, 1)
      except Exception as e:
        sublime.error_message(str(e.message))
        return

      regions = []
      print 'Duplicated'
      for r,c,cmt in self.checker_.errors_:
        start = self.view.text_point(r,c)
        end = start + len(cmt) + 2
        regions.append(sublime.Region(start,end))
        print r,c,cmt
      self.view.add_regions("hojuk_dup_tag", regions, "comment", "cross", sublime.DRAW_OUTLINED)

      regions = []
      print 'None-Tagged'
      for r,c,cmt in self.checker_.warnings_:
        start = self.view.text_point(r,c)
        end = start + len(cmt)
        regions.append(sublime.Region(start,end))
        print r,c,cmt
      self.view.add_regions("hojuk_no_tag_str", regions, "string", "cross", sublime.DRAW_OUTLINED)

    cur_pos = self.view.sel()[0].begin()
    regions = self.view.get_regions("hojuk_" + target)
    if len(regions) > 0:
      x = None
      try:
        nn = next(r for r in regions if r.begin() > cur_pos)
        x = nn
      except: #한바퀴 돌았당
        x = regions[0]
      self.view.sel().clear()
      self.view.sel().add(sublime.Region(x.begin()))

      self.view.show(x)

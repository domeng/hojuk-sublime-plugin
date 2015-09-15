# -*- encoding: utf-8 -*-
import sublime, sublime_plugin
from StringIO import StringIO
import xml.parsers.expat

ignore_data = ["外祖","統首","本","第","曾祖","戶","主","居","父","母","祖","年"]
reg_colors = {
  "hojuk_dup_tag" : "invalid",
  "hojuk_no_tag_str": "string",
  "hojuk_no_tag_str_global": "comment"
}

class HojukChecker: # xsd가 지원되지 않기 때문에 하드코딩

  def __init__(self, parser):
    parser.StartElementHandler = self.start_element
    parser.EndElementHandler  = self.end_element
    parser.CharacterDataHandler   = self.char_data
    self.parser_ = parser
    self.element_stack_ = [("root",[])]
    self.dup_list_ = []
    self.non_tag_local_ = []
    self.non_tag_global_ = []

  def start_element(self, name, attrs):
    par_name, par_list = self.element_stack_[-1]
    if name == u'사람': # 사람은 중복으로 존재가능 - 예외
      pass
    else:
      if name in par_list:
        self.dup_list_.append((self.parser_.CurrentLineNumber - 1, self.parser_.CurrentColumnNumber, name))
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
        self.non_tag_local_.append((self.parser_.CurrentLineNumber - 1, self.parser_.CurrentColumnNumber, data))
      elif len(self.element_stack_) <= 1:
        self.non_tag_global_.append((self.parser_.CurrentLineNumber - 1, self.parser_.CurrentColumnNumber, data))

class HojukCheckCommand(sublime_plugin.TextCommand):
  
  def run(self, edit, target):
    data = self.view.substr(sublime.Region(0, self.view.size()))
    is_refresh = False

    if not hasattr(self, 'old_data_') or self.old_data_ != data:
      self.old_data_ = data
      is_refresh = True

    if is_refresh:
      for reg in reg_colors.keys():
        self.view.erase_regions(reg)

      try:
        raw = data.encode('utf-8')
      except Exception as e: 
        sublime.error_message("UTF-8 문서가 아닙니다")
        return

      p = xml.parsers.expat.ParserCreate()
      checker = HojukChecker(p)
      try:
        p.Parse(raw, 1)
      except Exception as e:
        sublime.error_message(str(e.message))
        return

      global reg_colors

      regions = []
      for r,c,cmt in checker.dup_list_:
        start = self.view.text_point(r,c)
        end = start + len(cmt) + 2
        regions.append(sublime.Region(start,end))
      self.view.add_regions("hojuk_dup_tag", regions, reg_colors["hojuk_dup_tag"], "circle", sublime.DRAW_OUTLINED)

      regions = []
      for r,c,cmt in checker.non_tag_local_:
        start = self.view.text_point(r,c)
        end = start + len(cmt)
        regions.append(sublime.Region(start,end))
      self.view.add_regions("hojuk_no_tag_str", regions, reg_colors["hojuk_no_tag_str"], "dot", sublime.DRAW_OUTLINED)

      regions = []
      for r,c,cmt in checker.non_tag_global_:
        start = self.view.text_point(r,c)
        end = start + len(cmt)
        regions.append(sublime.Region(start,end))
      self.view.add_regions("hojuk_no_tag_str_global", regions, reg_colors["hojuk_no_tag_str_global"], "dot", sublime.DRAW_OUTLINED)

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
      self.view.erase_regions("hojuk_current_focus")
      self.view.add_regions("hojuk_current_focus", [x], reg_colors["hojuk_" + target])
      self.view.show(x)

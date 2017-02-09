import traceback
import threading

print "%s RELOADED" % __file__

from java.lang import Runnable
from org.eclipse.jface.action import Action
from org.eclipse.jface.action import MenuManager
from org.eclipse.jface.text import IDocument, TextSelection
from org.eclipse.jface.viewers import ISelectionProvider
from org.eclipse.swt import SWT
from org.eclipse.swt.widgets import Display
from org.eclipse.ui import PlatformUI
from org.eclipse.ui.texteditor import ITextEditor

"""
Add some menu items to Eclipse for modifying the selected text (that work even in non-Python editors)

To use these, 
1) install PyDev in Eclipse (e.g. under Help -> Eclipse Marketplace) and restart it
2) Open the Eclipse Preferences (on Windows it's under the Window menu)
3) Go to PyDev -> Scripting PyDev and set the location to the directory where you checked out this script.
4) Check the "Show the output given from the scripting to some console?" checkbox to see the output.
"""

# if we see menu items with these names, clear them
old_menu_item_names = set(["convert to dynamic cast"])

# don't try to show representations for properties with these names in debug output to avoid exceptions:
skip_keys = set(["enableAutoSave", "IPropertyChangeListener", "actionActivation", "blockSelectionMode", "blockSelectionModeEnabled",])


class EclipsePydevPluginHelper(object):
    def __init__(self):
        self.last_error_message = None
        
    def run_in_display(self, func):
        # https://stackoverflow.com/questions/1265174/nullpointerexception-in-platformui-getworkbench-getactiveworkbenchwindow-get
    
        # We can subclass java.lang.Runnable using normal python-style subclassing    
        class SelectedTextGetterRunnable(Runnable):
            def run(self):
                func()
    
        # and create an instance of it.
        runner = SelectedTextGetterRunnable()
        
        display = Display.getDefault()
        display.asyncExec(runner)

    def show_dir(self, obj):
        print "Imported object"
        print repr(obj)
        print dir(obj)
        for key in dir(obj):
            print key
            if key in skip_keys:
                continue 
    #         print "BEFORE GOT VALUE"
            try:
                value = getattr(obj, key)
            except Exception, e:
    #             print "HANDLING EXCEPTION"
                try:
                    print "EXCEPTION GETTING VALUE: %r" % e
                except:
                    print "EXCEPTION GETTING VALUE -- EXCEPTION UNPRINTABLE"
                continue
            except:
                print "OTHER EXCEPTION"
                continue
    #         print "GOT VALUE"
            try:
                print "%s: %r" % (key, value)
            except Exception, e:
                print "EXCEPTION SHOWING VALUE: %r" % e
                
    def error_msg(self, msg):
        # show the message in the pydev scripting console 
        print msg
        
        # Show the message in the eclipse status bar
        # https://wiki.eclipse.org/FAQ_How_do_I_write_a_message_to_the_workbench_status_line%3F
        
        # only show the error message for a limited amount of time
        timeout_s=2.0
        
        def within_display():
            workbench_window = PlatformUI.getWorkbench().getActiveWorkbenchWindow()
            
            if hasattr(workbench_window, "getActionBars"):
                
                bars = workbench_window.getActionBars()
                status_line_manager = bars.getStatusLineManager()
                status_line_manager.setErrorMessage(msg)

                # If this message is still on screen after a timeout, we will clear it
                self.last_error_message = msg

                def clearMessage():
#                     print "clearMessage()"
                    if self.last_error_message == msg:
#                         print "last message match"
                        print repr(status_line_manager)
                        try:
                            status_line_manager.setErrorMessage(None)
                        except:
                            print "well there was a problem of some kind"
                            print traceback.format_exc()
#                         print "message cleared"
                        
                def clearMessageInDisplay():
                    self.run_in_display(exception_wrap_func(clearMessage))
                
                threading.Timer(timeout_s, clearMessageInDisplay).start()
                
            else:
                print "ACTIVE WORKBENCH WINDOW does not have getActionBars()"
                
#             self.show_dir(workbench_window)

        self.run_in_display(within_display)


class EclipseMenuHelper(EclipsePydevPluginHelper):
    def add_menu_action(self, base_menu_to_put_in, action_name, action_callback, shortcut_modifiers=0, shortcut_key=None):
        # create action subclass with the run method that does what we want the action to do
        class TempMenuActionClass(Action):
            def with_selected_text(self, text):
                print text
                
            def run(self):
                action_callback()
        
        # create an instance of the action
        our_action = TempMenuActionClass(action_name)

        # https://wiki.eclipse.org/FAQ_How_do_I_provide_a_keyboard_shortcut_for_my_action%3F    
        if shortcut_key is not None:
            # FIXME make sure we support SWT constants (e.g. arrow keys) for shotcut_key
            assert isinstance(shortcut_key, str) and len(shortcut_key) == 1
            our_action.setAccelerator(shortcut_modifiers | ord(shortcut_key))
        
        # add it to the menu
        # https://wiki.eclipse.org/FAQ_How_do_I_build_menus_and_toolbars_programmatically%3F
        
        # a more complex menu interaction:
        # https://www.eclipse.org/forums/index.php/t/206613/
        
        def add_or_update_menu_item(menu_bar_manager):
            for cur_menu in menu_bar_manager.getItems():
                if isinstance(cur_menu, MenuManager):
#                     print cur_menu
                    cur_menu_name = cur_menu.getMenuText()
                    if cur_menu_name == base_menu_to_put_in:
                        # found the menu to put our item in
                        
                        # get rid of any existing item
                        
                        # ISSUE previously added menu items aren't materialized unless the menu has been opened, so won't be found to be removed
                        # FIXME fix duplicate menu items: materialize all menu items so that previous adds can be removed
                        cur_items = cur_menu.getMenuItems()
                        items_to_remove = []
                        for item in cur_items:
                            the_text = item.getText()
#                             print repr(the_text)
                            if the_text == action_name or the_text in old_menu_item_names:
    #                             show_dir(item)
                                data = item.getData()
#                                 show_dir(data)
#                                 print "removing %r" % data 
                                items_to_remove.append(data)
                                
                        items_to_remove.reverse()
#                         print len(items_to_remove)
                        for item in items_to_remove:
                            print "removing old menu item %r" % action_name
                            cur_menu.remove(item)
                        
                        # add the new item
                        print "adding new menu item %r"  % action_name
                        cur_menu.add(our_action)
                        break
            else:
                print "Couldn't find menu %r; no item added" % base_menu_to_put_in
                
        self.with_menu_bar_manager(add_or_update_menu_item)

    def with_menu_bar_manager(self, func):
        def within_display():
            workbench_window = PlatformUI.getWorkbench().getActiveWorkbenchWindow()
            
            assert workbench_window is not None
            
            menu_bar_manager = workbench_window.getMenuBarManager()
            assert menu_bar_manager is not None
            func(menu_bar_manager)
            
        self.run_in_display(within_display)


class EditorTextSelectionHelper(EclipsePydevPluginHelper):
    def __init__(self):
        self.last_workbench_window = None
        
    def get_text_editor(self):
        workbench_window = self.last_workbench_window
        if workbench_window is None:
            return None

        editor = workbench_window.getActivePage().getActiveEditor()

        is_text_editor = isinstance(editor, ITextEditor)
        
        print "is_text_editor: %r" % is_text_editor

        if is_text_editor:
            return editor
        else:
            return None
        
    def get_selected_text(self, callback):
        
        # Get the active editor and get text from it
        # http://stackoverflow.com/a/2395953/60422
        
        # this code doesn't normally have access to a workbench window, so run it in a display
        
        def within_display():
            workbench_window = PlatformUI.getWorkbench().getActiveWorkbenchWindow()
            
            assert workbench_window is not None
            self.last_workbench_window = workbench_window
            
            editor = self.get_text_editor()
            
#             show_dir(workbench_window)
            if editor is not None:
                selection = editor.getSelectionProvider().getSelection()
                selected_text = selection.getText()
                print "selection: %r" % selected_text 
                callback(selected_text)
                
        self.run_in_display(within_display)
    #             show_dir(editor)
    
    def set_selection(self, document, selection_provider, offset, length):
        assert isinstance(document, IDocument)
        assert isinstance(selection_provider, ISelectionProvider)
        new_selection = TextSelection(document, offset, length)
        selection_provider.setSelection(new_selection)
        
    
    def replace_selection_text(self, text, new_selection_offset=None, new_selection_length=None):
        """
        Replace the selected text with the given text
        @param text: text to replace the selected text with
        @param new_selection_offset: (optional) if a new selection should be set, offset of the new selection relative to the old one
        @param new_selection_length: (optional) if a new selection should be set, length of the new selection 
        """
        print "set selection text: %r" % text
        editor = self.get_text_editor()
        if editor is None:
            print "Can't set selection -- don't have editor"
            return
        
        selection_provider = editor.getSelectionProvider()
        selection = selection_provider.getSelection()
        
        if selection is None:
            print "selection was None"
            return
        
        offset = selection.offset
        length = selection.length
        document = selection.getDocument()
        
        document.replace(offset, length, text)
        
        if new_selection_offset is not None and new_selection_length is not None:
            # set the desired new selection
            self.set_selection(document, selection_provider, offset + new_selection_offset, new_selection_length)

def has_balanced_parens(s):
    paren_depth = 0
    for ch in s:
        if ch == "(":
            paren_depth += 1
        if ch == ")":
            paren_depth -= 1
        if paren_depth < 0:
            return False
        
    return paren_depth == 0


class SelectedTextChanger(EditorTextSelectionHelper, EclipseMenuHelper):
    def __init__(self):
        pass
        
    def create_menu_items(self):
        self.add_menu_action("&Edit", "convert to static cast", exception_wrap_func(self.on_convert_to_static_cast), shortcut_modifiers=SWT.CTRL, shortcut_key='2')
        self.add_menu_action("&Edit", "convert to reinterpret cast", exception_wrap_func(self.on_convert_to_reinterpret_cast), shortcut_modifiers=SWT.CTRL, shortcut_key='4')
        
    def on_convert_to_static_cast(self):
        return self.on_convert_to_cast("static_cast")
    
    def on_convert_to_reinterpret_cast(self):
        return self.on_convert_to_cast("reinterpret_cast")

    def on_convert_to_cast(self, new_cast_keyword):
        print "setup for %r" % new_cast_keyword

        def with_selected_text(text):
            if not text.startswith("("):
                return self.error_msg("selection doesn't start with a C-style cast")
            
            parens_count = 1
            for in_pos, ch in enumerate(text[1:]):
                pos = in_pos + 1
#                 print parens_count, pos, ch
                if ch == "(":
                    parens_count += 1
                if ch == ")":
                    parens_count -= 1
                if parens_count == 0:
                    break
            
            cast_end = pos + 1
            
            c_style_cast = text[:cast_end]
            expression_text = text[cast_end:]
            
            print repr(c_style_cast), repr(expression_text)
            
            if not c_style_cast.endswith(")"):
                return self.error_msg("selection does not contain a complete C-style cast")
            
            casted_to_type = c_style_cast[1:-1]
            
            # if there's a semicolon at the end of the expression, leave it outside the cast
            suffix = ""
            if expression_text.endswith(";"):
                suffix = ";"
                expression_text = expression_text[:-1]

            # remove redundant parens around the expression that is being cast
            if expression_text.startswith("(") and expression_text.endswith(")") and has_balanced_parens(expression_text[1:-1]):
                expression_text = expression_text[1:-1]
                
            if expression_text == "":
                return self.error_msg("expression is empty")
                
            if not has_balanced_parens(expression_text):
                return self.error_msg("expression %r has unbalanced parens" % expression_text)
                        
            new_text = "%s<%s>(%s)%s" % (new_cast_keyword, casted_to_type, expression_text, suffix)
            
            print "new text %r" % new_text
            
            # We'll leave the value part of that selected, so that if there is a nested cast the user can do a conversion on it right away
            new_selection_offset = len(new_cast_keyword) + len(casted_to_type) + 3
            new_selection_length = len(expression_text)
            
            self.replace_selection_text(new_text, new_selection_offset=new_selection_offset, new_selection_length=new_selection_length)
        
        self.get_selected_text(exception_wrap_func(with_selected_text))        


def func_main():

    # create an action for this
        
    # test run get_selected_text immediately
    
    def show(text):
        print "HERE"
#         print "SELECTED TEXT: %r" % text

#     get_selected_text(show)
    obj = SelectedTextChanger()
    obj.create_menu_items()
    
    
def exception_run_func(func, *args, **kwargs):
    try:
        func(*args, **kwargs)
    except Exception, e:
        print "EXCEPTION:"
        try:
            print e
        except:
            pass
        print traceback.format_exc()
    

def exception_wrap_func(func):
#     print "IN EXCEPTION WRAP FUNC %r" % func
    def wrapper(*args, **kwargs):
#         print "IN EXCEPTION WRAP FUNC %r WRAPPER" % func
        exception_run_func(func, *args, **kwargs)
            
    return wrapper


try:
    exception_run_func(func_main)
except Exception, e:
    print "EXCEPTION:"
    try:
        print e
    except:
        pass
    print traceback.format_exc()

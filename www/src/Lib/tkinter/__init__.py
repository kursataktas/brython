import re

import javascript
from browser import console, document, html, window

_loops = []
_selected = [] # list of selected windows


fontFamily = 'Arial'
color = '#000'
backgroundColor = '#f0f0f0'
borderColor = '#008'
title_bgColor = '#fff'
title_color = '#000'

class Constant:

    def __init__(self, value):
        self.value = value

    def __eq__(self, other):
        return other is self \
            or isinstance(other, str) and other.upper() == self.value

    def __repr__(self):
        return f'<Constant {self.value}>'

E = Constant('E')
W = Constant('W')
N = Constant('N')
S = Constant('S')
NW = Constant('NW')
NE = Constant('NE')
SW = Constant('SW')
SE = Constant('SE')

NORMAL = Constant('NORMAL')
ACTIVE = Constant('ACTIVE')
DISABLED = Constant('DISABLED')
END = Constant('END')
SINGLE = Constant('SINGLE')
BROWSE = Constant('BROWSE')
MULTIPLE = Constant('MULTIPLE')
EXTENDED = Constant('EXTENDED')

# pack() option 'side'
LEFT = Constant('LEFT')
RIGHT = Constant('RIGHT')
TOP = Constant('TOP')
BOTTOM = Constant('BOTTOM')

# pack() option 'fill'
NONE = Constant('NONE')
BOTH = Constant('BOTH')
X = Constant('X')
Y = Constant('Y')


INSERT = Constant('INSERT')
CURRENT = Constant('CURRENT')

class _Packed:

    def __init__(self, widget, side, fill, expand, padx, pady, ipadx, ipady):
        self.widget = widget
        self.side = side
        self.fill = fill
        self.expand = expand
        self.padx = padx
        self.pady = pady
        self.ipadx = ipadx
        self.ipady = ipady
        self.anchor = 'center'

class Cavity:

    def __init__(self, left, top, width, height):
        self.left = left
        self.top = top
        self.width = width
        self.height = height

class _Packer:

    def __init__(self, widget):
        self.widget = widget

    def process(self):
        self.compute_dimensions()

        for elt in self.widget._packed:
            self.compute_parcel_dimensions(elt)
            self.compute_content_dimensions(elt)
            self.position_content_in_parcel(elt)

            """element = elt.widget.element
            element.style.position = 'absolute'
            element.style.left = f'{elt.left}px'
            element.style.top = f'{elt.top}px'
            element.style.width = f'{elt.content_width}px'
            element.style.height = f'{elt.content_height}px'

            self.container <= element"""


    def compute_content_dimensions(self, elt):
        """The packer chooses the dimensions of the content. The width will
        normally be the content's requested width plus twice its -ipadx option
        and the height will normally be the content's requested height plus
        twice its -ipady option. However, if the -fill option is x or both
        then the width of the content is expanded to fill the width of the
        parcel, minus twice the -padx option. If the -fill option is y or both
        then the height of the content is expanded to fill the width of the
        parcel, minus twice the -pady option.
        """
        parcel = elt.parcel
        if elt.fill in [X, BOTH]:
            elt.content_width = parcel.offsetWidth - 2 * elt.padx
        else:
            elt.content_width = elt.content_req_width

        if elt.fill in [Y, BOTH]:
            elt.content_height = parcel.offsetHeight - 2 * elt.pady
        else:
            elt.content_height = elt.content_req_height

    def compute_parcel_dimensions(self, elt):
        """The packer allocates a rectangular parcel for the content along the
        side of the cavity given by the content's -side option. If the side is
        top or bottom then the width of the parcel is the width of the cavity
        and its height is the requested height of the content plus the -ipady
        and -pady options. For the left or right side the height of the parcel
        is the height of the cavity and the width is the requested width of
        the content plus the -ipadx and -padx options.
        The parcel may be enlarged further because of the -expand option.
        """
        if elt.side in [TOP, BOTTOM]:
            parcel_width = self.cavity.width
            parcel_height = elt.content_req_height
            if elt.expand:
                parcel_height += self.expand_height
        else:
            parcel_height = self.cavity.height
            parcel_width = elt.content_req_width
            if elt.expand:
                parcel_width += self.expand_width

        if elt.side == LEFT:
            parcel_left = self.cavity.left
            parcel_top = self.cavity.top
            self.cavity.left += parcel_width
            self.cavity.width -= parcel_width
        elif elt.side == RIGHT:
            parcel_left = self.cavity.left + self.cavity.width - self.content_width
            self.cavity.width -= parcel_width
        elif elt.side == TOP:
            parcel_left = self.cavity.left
            parcel_top = self.cavity.top
            elt.left = 0
            self.cavity.top += parcel_height
            self.cavity.height -= parcel_height
        elif elt.side == BOTTOM:
            parcel_top = self.cavity.top + self.cavity.height - elt.content_height
            parcel_left = self.cavity.left
            self.cavity.height -= parcel_height

        parcel = elt.parcel = html.SPAN(style="position:absolute;")
        parcel.style.left = f'{parcel_left}px'
        parcel.style.top = f'{parcel_top}px'
        parcel.style.width = f'{parcel_width}px'
        parcel.style.height = f'{parcel_height}px'
        parcel.style.display = 'flex'
        parcel.style.alignItems = 'center'
        parcel.style.justifyContent = 'center'

        self.container <= parcel

    def position_content_in_parcel(self, elt):
        """If the content is smaller than the parcel then the -anchor option
        determines where in the parcel the content will be placed. If -padx or
        -pady is non-zero, then the given amount of external padding will
        always be left between the content and the edges of the parcel.
        """
        parcel = elt.parcel
        content = elt.widget.element
        content.style.width = f'{elt.content_width}px'
        content.style.height = f'{elt.content_height}px'
        content.style.display = 'flex'
        content.style.alignItems = 'center'
        content.style.justifyContent = 'center'
        parcel <= content

    def compute_dimensions(self):
        container = self.widget.element
        left = 0
        width = container.offsetWidth
        top = 0
        height = container.offsetHeight
        toplevel = isinstance(self.widget, Tk) \
            and self.widget.title_bar.style.display != 'none'
        if toplevel:
            top += self.widget.title_bar.offsetHeight
            height -= self.widget.title_bar.offsetHeight
            container = self.widget.panel

        # At the time it processes each content, a rectangular area within the
        # container is still unallocated. This area is called the cavity; for
        # the first content it is the entire area of the container.
        self.cavity = Cavity(left, top, width, height)

        self.container = container

        container.clear()

        # fake hidden DIV to determine the defaut dimensions of widgets
        fake_container = html.DIV(style='position:absolute;visibility:hidden;')
        document <= fake_container
        
        nb_expand_x = 0 # number of widgets with side = LEFT/RIGHT and expand
        nb_expand_y = 0 # number of widgets with side = TOP/BOTTOM and expand
        width_required_by_left_right = 0
        height_required_by_top_bottom = 0
        container_req_width = 0
        container_req_height = 0
        for packed in self.widget._packed:
            content = packed.widget.element
            fake_container <= content
            # content's requested width and height (including padding)
            content_req_width = content.offsetWidth + 2 * packed.ipadx
            content_req_height = content.offsetHeight + 2 * packed.ipady
            packed.content_req_height = content_req_height
            packed.content_req_width = content_req_width
            if packed.expand:
                if packed.side in [TOP, BOTTOM]:
                    nb_expand_y += 1
                else:
                    nb_expand_x += 1
            if packed.side in [TOP, BOTTOM]:
                container_req_height += content_req_height
                height_required_by_top_bottom += content_req_height
                if width_required_by_left_right + content_req_width > container_req_width:
                    container_req_width = width_required_by_left_right + content_req_width
            else:
                container_req_width += content_req_width
                width_required_by_left_right += content_req_width
                if height_required_by_top_bottom + content_req_height > container_req_height:
                    container_req_height = height_required_by_top_bottom + content_req_height

        if container_req_width > width:
            width = container_req_width
            container.style.width = f'{width}px'
        if container_req_height > height:
            dh = container_req_height - height
            height = container_req_height
            container.style.height = f'{container.offsetHeight + dh}px'
        if nb_expand_x:
            self.expand_width = (width - container_req_width) / nb_expand_x
        if nb_expand_y:
            self.expand_height = (height - container_req_height) / nb_expand_y

        fake_container.remove()


class Widget:

    def __getitem__(self, option):
        value = self.cget(option)
        if value is None:
            raise KeyError(option)
        return value

    def cget(self, option):
        if option not in self.keys():
            raise ValueError(f"unknown option '{key}")
        return self.kw.get(option)

    def config(self, **kw):
        keys = self.keys()
        for key, value in kw.items():
            if key not in keys:
                raise ValueError(f"unknown option '{key}")

        if (text := kw.get('text')) is not None:
            self.element.text = text

        # dimensions
        if (width := kw.get('width')) is not None:
            self.element.style.width = f'{width}em'
        if (height := kw.get('height')) is not None:
            if isinstance(self, Listbox):
                self.element.attrs['size'] = height
            else:
                self.element.style.height = f'{height}em'
        if (padx := kw.get('padx')) is not None:
            self.element.style.paddingLeft = f'{padx}px'
            self.element.style.paddingRight = f'{padx}px'
        if (pady := kw.get('pady')) is not None:
            self.element.style.paddingTop = f'{pady}px'
            self.element.style.paddingBottom = f'{pady}px'

        # colors
        if (bg := kw.get('bg')) is not None \
                or (bg := kw.get('background')) is not None:
            self.element.style.backgroundColor = bg
            self.kw['bg'] = self.kw['background'] = bg
        if (fg := kw.get('fg')) is not None \
                or (fg := kw.get('foreground')) is not None:
            self.element.style.color = fg
            self.kw['fg'] = self.kw['foreground'] = fg
        if (bd := kw.get('bd')) is not None \
                or (bd := kw.get('borderwidth')) is not None:
            self.element.style.borderWidth = f'{bd}px'
            self.element.style.borderStyle = 'solid'
            self.element.style.borderColor = '#ddd'
            self.element.style.boxShadow = "3px 3px 5px #999999"
            self.kw['bd'] = self.kw['borderwidth'] = bd

        # font
        if (font := kw.get('font')) is not None:
            for key, value in font.css.items():
                setattr(self.element.style, key, value)

        # misc
        if (cursor := kw.get('cursor')) is not None:
            self.element.style.cursor = cursor

        if (command := kw.get('command')) is not None:
            self.element.bind('click', lambda ev: command())

        if (state := kw.get('state')) is not None:
            if state is DISABLED:
                self.element.attrs['disabled'] = True
            elif state is NORMAL:
                self.element.attrs['disabled'] = False

        if (menu := kw.get('menu')) is not None:
            if isinstance(self, Tk):
                menu._build()
                self.element.insertBefore(menu.element,
                    self.title_bar.nextSibling)
                self.menu = menu

        if selectmode := kw.get('selectmode') is not None:
            self.element.attrs['multiple'] = selectmode is MULTIPLE

        self.kw |= kw

    configure = config

    def grid(self, **kwargs):
        td = grid(self.master, **kwargs)
        td <= self.element

    def pack(self, side=TOP, fill=NONE, expand=0, in_=None,
            ipadx=0, ipady=0, padx=0, pady=0):
        master = self.master
        packed = _Packed(self, side, fill, expand, padx, pady, ipadx, ipady)
        if not hasattr(master, "_packed"):
            master._packed = [packed]
        else:
            master._packed.append(packed)

    def _pack(self):
        """Packer algorithm.
        See https://www.tcl.tk/man/tcl/TkCmd/pack.html
        """
        _Packer(self).process()
        return
        container = self
        left = 0
        width = self.element.offsetWidth
        top = 0
        height = self.element.offsetHeight
        toplevel = isinstance(self, Tk) \
            and self.title_bar.style.display != 'none'
        if toplevel:
            top += self.title_bar.offsetHeight
            height -= self.title_bar.offsetHeight
            container = self.panel
        else:
            container = self
        print('\nPack new element in master', left, top, width, height)
        container.clear()

        # fake hidden DIV to determine the defaut dimensions of widgets
        fake_container = html.DIV(style='position:absolute;visibility:hidden;')
        document <= fake_container
        print('Default widget dimensions')
        nb_expand_x = 0
        nb_expand_y = 0
        width_required_by_left_right = 0
        height_required_by_top_bottom = 0
        container_req_width = 0
        container_req_height = 0
        for packed in self._packed:
            content = packed.widget.element
            fake_container <= content
            # content's requested width and height (including padding)
            content_req_width = content.offsetWidth
            content_req_height = content.offsetHeight
            if packed.expand:
                if packed.fill in [X, BOTH]:
                    nb_expand_x += 1
                if packed.fill in [Y, BOTH]:
                    nb_expand_y += 1
            if packed.side in [TOP, BOTTOM]:
                container_req_height += content_req_height
                height_required_by_top_bottom += content_req_height
                if width_required_by_left_right + content_req_width > container_req_width:
                    container_req_width = width_required_by_left_right + content_req_width
            else:
                container_req_width += content_req_width
                width_required_by_left_right += content_req_width
                if height_required_by_top_bottom + content_req_height > container_req_height:
                    container_req_height = height_required_by_top_bottom + content_req_height
        print('min width required by LEFT RIGHT', width_required_by_left_right)
        print('min height required by TOP BOTTOM', height_required_by_top_bottom)
        print('min required width', container_req_width, 'master w', width)
        print('min required height', container_req_height, 'master h', height)

        if container_req_width > width:
            width = container_req_width
            container.style.width = f'{width}px'
        if container_req_height > height:
            dh = container_req_height - height
            height = container_req_height
            container.style.height = f'{container.offsetHeight + dh}px'
        width_available_for_expand = width - container_req_width
        height_available_for_expand = height - container_req_height

        fake_container.remove()

        # At the time it processes each content, a rectangular area within the
        # container is still unallocated. This area is called the cavity; for
        # the first content it is the entire area of the container.
        cavity = container

        for elt in self._packed:
            # determine parcel dimensions

            element = elt.widget.element
            element.style.position = 'absolute'
            element.style.display = 'block'
            element.style.boxSizing = 'border-box'

            console.log(elt.widget.element.text, elt, 'top', top, 'left', left)
            if elt.side == LEFT and elt.fill in [Y, BOTH]:
                # wrap in a container for vertical align
                wrapper = html.SPAN(element, style=element.style.cssText)
                wrapper.style.padding = '0px'
                wrapper.style.border = '0px'
                wrapper.style.boxSizing = 'border-box'
                container <= wrapper
                elt_width = element.offsetWidth
                element = wrapper
                element.style.position = 'absolute'
                element.style.display = 'flex'
                element.style.alignItems = 'center'
                element.style.width = f'{elt_width + 1}px'
                console.log('replace by container', element)
                console.log('element.style.width', element.style.width, 'offset', element.offsetWidth)
                console.log('original', element.firstChild.offsetWidth)
            elif elt.fill in [X, BOTH]:
                element.style.textAlign = 'center'
                container <= element
            else:
                container <= element

            element.style.top = f'{top}px'
            element.style.left = f'{left}px'

            if elt.fill in [Y, BOTH]:
                # Compute element height
                # If 'expand' is not set, and there are no widgets packed
                # with fill Y and expand, use all available height
                print('elt', elt.widget.element.text, 'fill', elt.fill,
                    'expand', elt.expand, 'nb expand y', nb_expand_y)
                if not elt.expand and nb_expand_y == 0:
                    console.log('all height', height)
                    element.style.height = f'{height}px'
                    console.log('element filled', element.offsetHeight)
                    console.log('title bar', master.title_bar.offsetHeight)
                    console.log('matser', master.element.offsetHeight)
                    for child in master.element.childNodes:
                        print('child', child, child.offsetHeight)
                # If 'expand', add a portion of the space available for
                # expand
                elif elt.expand:
                    extra_height = round(height_available_for_expand /
                                         nb_expand_y)
                    expanded_height = element.offsetHeight + extra_height
                    element.style.height = f'{extended_height}px'

            if elt.fill in [X, BOTH]:
                # Compute element width
                # If 'expand' is not set, and there are no widgets packed
                # with fill X and expand, use all available width
                print('elt', elt.widget.element.text, 'fill', elt.fill,
                    'expand', elt.expand, 'nb expand x', nb_expand_x)
                if not elt.expand and nb_expand_x == 0:
                    console.log('use all width', width)
                    element.style.width = f'{width}px'
                    console.log('offsetWidth', element.offsetWidth)
                # If 'expand', add a portion of the space available for
                # expand
                elif elt.expand:
                    extra_width = round(width_available_for_expand /
                                         nb_expand_x)
                    expanded_width = element.offsetWidth + extra_width
                    element.style.width = f'{extended_width}px'

            filled_X = elt.fill in [X, BOTH]
            filled_Y = elt.fill in [Y, BOTH]

            print(elt.widget.element.text, 'filled X', filled_X, 'filled Y', filled_Y)
            # if side is LEFT or RIGHT and no fill X, center vertically

            if elt.side in [LEFT, RIGHT] and not filled_Y:
                # center vertically
                elt_top = top + (height - element.offsetHeight) / 2
                element.style.top = f'{elt_top}px'
            elif elt.side in [TOP, BOTTOM] and not filled_X:
                # center horizontally
                elt_left = left + (width - element.offsetWidth) / 2
                element.style.left = f'{elt_left}px'

            if elt.side == LEFT:
                left += element.offsetWidth
                console.log('width before element left', width)
                width -= element.offsetWidth
                console.log('width after', width)
            elif elt.side == RIGHT:
                width -= element.offsetWidth
            elif elt.side == TOP:
                top += element.offsetHeight
                height -= element.offsetHeight
            elif elt.side == BOTTOM:
                height -= element.offsetHeight
            print('new top left', top, left)


    def _root(self):
        master = self.master
        while not isinstance(master, Tk):
            master = master.master
        return master

class Tk(Widget):
    """Basic, moveable dialog box with a title bar.
    """

    _main_style = {
        'position': 'absolute',
        'left': f'{int(0.1 * window.innerWidth)}px',
        'top': f'{int(0.1 * window.innerHeight)}px',
        #'width': f'{int(window.outerWidth * 0.2)}px',
        #'height': f'{int(window.outerHeight * 0.2)}px',
        'font-family': fontFamily,
        'z-index': 10,
        'resize': 'both',
        'overflow': 'hidden',
        'visibility': 'hidden'
    }

    _title_style = {
        'background-color': title_bgColor,
        'color': title_color,
        'border-style': 'solid',
        'border-color': borderColor,
        'border-width': '0px',
        'padding': '0.4em',
        'cursor': 'default'
    }

    _close_button_style = {
        'float': 'right',
        'color': color,
        'cursor': 'default',
        'padding': '0.1em'
    }

    _panel_style = {
        'background-color': backgroundColor
    }

    _default_config = {
        'bg': backgroundColor,
        'relief': 'solid',
        'bd': 1
    }

    def __init__(self, **kw):
        self.element = html.DIV(style=self._main_style)

        self.title_text = html.SPAN()
        self.title_text.html = '&nbsp;'
        self.title_bar = html.DIV('tk' + 3 * chr(160) + self.title_text,
            style=self._title_style)
        self.element <= self.title_bar
        self.close_button = html.SPAN("&times;",
            style=self._close_button_style)
        self.title_bar <= self.close_button
        self.close_button.bind("click", self.close)
        self.panel = html.DIV(style=self._panel_style)
        self.element <= self.panel

        self.kw = self._default_config | kw

        document <= self.element

        self.title_bar.bind("mousedown", self._grab_widget)
        self.element.bind("leave", self._mouseup)

        self._maxsize = (None, None)
        #self.minsize(int(window.outerWidth * 0.2),
        #                int(window.outerHeight * 0.2))
        self.resizable(1, 1)

        self.menu = None

        self.config(**self.kw)

        _loops.append(self)

    def aspect(self, *args):
        raise NotImplementedError()

    def close(self, *args):
        self.element.remove()

    def deiconify(self):
        self.element.style.visibility = "visible"
        self._state = "normal"

    def geometry(self, coords=None):
        if coords is None:
            return (f'{self.widget.width}x{self.widget.height}+'
                    f'{self.widget.abs_left}+{self.widget.abs_top}')
        else:
            values = {}
            whxy = coords.split('x')
            if len(whxy) > 2:
                raise ValueError(f'bad geometry specifier "{coords}"')
            try:
                values['width'] = int(whxy[0])
            except:
                raise ValueError(f'bad geometry specifier "{coords}"')
            if len(whxy) > 2:
                raise ValueError(f'bad geometry specifier "{coords}"')
            elif len(whxy) == 2:
                hxy = whxy[1].split('+')
                if len(hxy) > 3:
                    raise ValueError(f'bad geometry specifier "{coords}"')
                for key, value in zip(['height', 'left', 'top'], hxy):
                    try:
                        values[key] = int(value)
                    except:
                        raise ValueError(f'bad geometry specifier "{coords}"')
            for key, value in values.items():
                setattr(self.element.style, key, f'{value}px')
            panel_height = self.element.offsetHeight - self.title_bar.offsetHeight
            self.panel.style.height = f'{panel_height}px'
            self.panel.style.width = f'{self.element.offsetWidth}px'
            
    def keys(self):
        return ['bd', 'borderwidth', 'class', 'menu', 'relief', 'screen',
            'use', 'background', 'bg', 'colormap', 'container', 'cursor',
            'height', 'highlightbackground', 'highlightcolor',
            'highlightthickness', 'padx', 'pady', 'takefocus', 'visual',
            'width']

    def iconify(self):
        raise NotImplementedError()

    def maxsize(self, width=None, height=None):
        if width is None and height is None:
            return self._maxsize
        self._maxsize = (width, height)
        if width is not None:
            self.element.style.maxWidth = f'{width}px'
        if height is not None:
            self.element.style.maxHeight = f'{height}px'

    def minsize(self, width=None, height=None):
        if width is None and height is None:
            return self._minsize
        self._minsize = (width, height)
        if width is not None:
            self.element.style.minWidth = f'{width}px'
        if height is not None:
            self.element.style.minHeight = f'{height}px'

    def resizable(self, width=None, height=None):
        if width is None:
            css = self.element.style.resize
            match css:
                case 'both':
                    return (1, 1)
                case 'horizontal':
                    return (1, 0)
                case 'vertical':
                    return (0, 1)
                case 'non':
                    return (1, 0)
        else:
            if height is None:
                raise ValueError('missing value for height')
            height = self._resizable[1] if height is None else height
            match (width, height):
                case (0, 0):
                    self.element.style.resize = 'none'
                case (0, 1):
                    self.element.style.resize = 'vertical'
                case (1, 0):
                    self.element.style.resize = 'horizontal'
                case (1, 1):
                    self.element.style.resize = 'both'

    def mainloop(self):
        if hasattr(self, '_packed'):
            self._pack()
        self.element.style.visibility = "visible"

    def overrideredirect(self, flag=None):
        if flag is None:
            return self._overrideredirect
        self._overrideredirect = flag
        if flag:
            self.title_bar.style.display = 'none'
        else:
            self.title_bar.style.display = 'block'

    def quit(self):
        self.element.remove()

    def state(self):
        return self._state

    def title(self, title=None):
        if title is None:
            return self.title_text.text
        self.title_text.text = title

    def withdraw(self):
        self.element.style.visibility = 'hidden'
        self._state = 'withdrawn'

    def _grab_widget(self, event):
        self._remove_menus()
        _selected = [self]
        document.bind("mousemove", self._move_widget)
        document.bind("mouseup", self._stop_moving_widget)
        self.initial = [self.element.left - event.x,
                        self.element.top - event.y]
        # prevent default behaviour to avoid selecting the moving element
        event.preventDefault()

    def _move_widget(self, event):
        # set new moving element coordinates
        self.element.left = self.initial[0] + event.x
        self.element.top = self.initial[1] + event.y

    def _remove_menus(self):
        if self.menu and self.menu.open_submenu:
            self.menu.open_on_mouseenter = False
            self.menu.open_submenu.element.remove()

    def _stop_moving_widget(self, event):
        document.unbind('mousemove')
        document.unbind('mouseup')

    def _mouseup(self, event):
        document.unbind("mousemove")
        document.unbind("touchmove")





def grid(master, column=0, columnspan=1, row=None, rowspan=1,
        in_=None, ipadx=None, ipady=None,
        sticky=''):
    if not hasattr(master, 'table'):
        master.table = html.TABLE(width='100%')
        master.element <= master.table
    if not hasattr(master, 'cells'):
        master.cells = set()
    # The cell at (row, column) in grid must be inserted in table row #row
    # master.cells is a set of (row, column) that are already used because
    # a cell with colspan or rowspan is used

    if row is None:
        # default is the first empty row
        row = len(master.table.rows)

    nb_rows = len(master.table.rows)
    for i in range(row - nb_rows + 1):
        master.table <= html.TR()

    tr = master.table.rows[row]
    # number of TD in table row
    nb_cols = len(tr.cells)
    # cells in row occupied because of rowspan / colspan
    cols_from_span = [c for (r, c) in master.cells
        if r == row and c < column]

    cols_to_add = nb_cols + len(cols_from_span)
    for i in range(column - cols_to_add + 1):
        tr <= html.TD()

    td = tr.cells[column - len(cols_from_span)]

    # update cells
    for i in range(1, rowspan):
        for j in range(columnspan):
            master.cells.add((row + i, column + j))
    for i in range(rowspan):
        for j in range(1, columnspan):
            master.cells.add((row + i, column + j))

    if columnspan > 1:
        td.attrs['colspan'] = columnspan
    if rowspan > 1:
        td.attrs['rowspan'] = rowspan

    if isinstance(sticky, Constant):
        sticky = list(sticky.value)
    else:
        sticky = list(sticky)

    #td.style.textAlign = 'center' # default

    if 'W' in sticky:
        td.style.textAlign = 'left'
    if 'E' in sticky:
        td.style.textAlign = 'right'
    if 'N' in sticky:
        td.style.verticalAlign = 'top'
    if 'S' in sticky:
        td.style.verticalAlign = 'bottom'
    return td

class IntVar:

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class Button(Widget):

    def __init__(self, master, text='', **kw):
        self.master = master
        self.kw = kw
        self.element = html.BUTTON(text)
        self.config(**kw)

    def keys(self):
        return ['activebackground', 'activeforeground', 'anchor',
            'background', 'bd', 'bg', 'bitmap', 'borderwidth', 'command',
            'compound', 'cursor', 'default', 'disabledforeground', 'fg',
            'font', 'foreground', 'height', 'highlightbackground',
            'highlightcolor', 'highlightthickness', 'image', 'justify',
            'overrelief', 'padx', 'pady', 'relief', 'repeatdelay',
            'repeatinterval', 'state', 'takefocus', 'text', 'textvariable',
            'underline', 'width', 'wraplength']

class Entry(Widget):

    def __init__(self, master, **kw):
        self.master = master
        self.kw = kw
        self.element = html.INPUT()
        self.config(**kw)

    def keys(self):
        return ['background', 'bd', 'bg', 'borderwidth', 'cursor',
            'disabledbackground', 'disabledforeground', 'exportselection',
            'fg', 'font', 'foreground', 'highlightbackground',
            'highlightcolor', 'highlightthickness', 'insertbackground',
            'insertborderwidth', 'insertofftime', 'insertontime',
            'insertwidth', 'invalidcommand', 'invcmd', 'justify',
            'readonlybackground', 'relief', 'selectbackground',
            'selectborderwidth', 'selectforeground', 'show', 'state',
            'takefocus', 'textvariable', 'validate', 'validatecommand',
            'vcmd', 'width', 'xscrollcommand']

class Frame(Widget):

    def __init__(self, master, **kw):
        self.master = master
        self.kw = kw
        self.element = html.DIV()
        self.config(**kw)

    def keys(self):
        return ['bd', 'borderwidth', 'class', 'relief', 'background', 'bg',
            'colormap', 'container', 'cursor', 'height', 'highlightbackground',
            'highlightcolor', 'highlightthickness', 'padx', 'pady',
            'takefocus', 'visual', 'width']

class Label(Widget):

    def __init__(self, master, *, text='', **kw):
        self.master = master
        self.text = text
        self.kw = kw
        self.element = html.SPAN(text, style={'white-space': 'pre'})
        self.config(**kw)

    def keys(self):
        return ['activebackground', 'activeforeground', 'anchor',
            'background', 'bd', 'bg', 'bitmap', 'borderwidth', 'compound',
            'cursor', 'disabledforeground', 'fg', 'font', 'foreground',
            'height', 'highlightbackground', 'highlightcolor',
            'highlightthickness', 'image', 'justify', 'padx', 'pady',
            'relief', 'state', 'takefocus', 'text', 'textvariable',
            'underline', 'width', 'wraplength']


class Listbox(Widget):

    def __init__(self, master, **kw):
        self.master = master
        self.kw = kw
        self.element = html.SELECT()
        self.config(**kw)

    def delete(self, position):
        if position is END:
            position = len(self.element.options) - 1
        elif position is ACTIVE:
            position = self.element.selectedIndex
        self.element.remove(position)

    def insert(self, position, *options):
        if position is END:
            for option in options:
                self.element <= html.OPTION(option)
            return
        elif position is ACTIVE:
            position = self.element.selectedIndex
        for option in options.reverse():
            self.element.add(html.OPTION(option), position)

    def keys(self):
        return ['activestyle', 'background', 'bd', 'bg', 'borderwidth',
            'cursor', 'disabledforeground', 'exportselection', 'fg', 'font',
            'foreground', 'height', 'highlightbackground', 'highlightcolor',
            'highlightthickness', 'justify', 'relief', 'selectbackground',
            'selectborderwidth', 'selectforeground', 'selectmode', 'setgrid',
            'state', 'takefocus', 'width', 'xscrollcommand', 'yscrollcommand',
            'listvariable']

    def size(self):
        return len(self.element.options)

class Menu(Widget):

    _main_menu_style = {
        'border-color': borderColor,
        'border-width': '0px',
        'width': '100%',
        'cursor': 'default',
        'padding': '5px 0px 5px 0px'
    }

    _main_menu_span_style = {
        'padding': '0em 1em 0em 0.5em'
    }

    _submenu_style = {
        'position': 'absolute',
        'border-color': borderColor,
        'width': 'auto',
        'cursor': 'default'
    }

    _submenu_label_style = {
        'padding-left': '0.5em',
        'padding-right': '0px',
        'width': '80%'
    }

    _submenu_arrow_style = {
        'text-align': 'right',
        'padding-left': '3px',
        'padding-right': '5px'
    }

    _default_config_main = {
        'activebackground': '#0078d7',
        'background': backgroundColor,
        'foreground' : color
    }

    _default_config = {
        'activebackground': '#0078d7',
        'background': backgroundColor,
        'bd': 1,
        'foreground' : color
    }

    def __init__(self, master, **kw):
        self.master = master
        self.toplevel = isinstance(master, Tk)
        if self.toplevel:
            master.menu = self
            self.kw = self._default_config_main | kw
        else:
            self.kw = self._default_config | kw

        self.selected = None
        self.open_submenu = None
        self.open_on_mouseenter = False
        self._ignore_next_key_events = False

        self.choices = []

    def add_cascade(self, **kw):
        """Add a command that triggers the opening of 'menu', an instance of
        Menu.
        submenu = Menu(main_menu)
        main_menu.add_cascade('open', submenu)
        """
        self.choices.append(kw | {'type': 'cascade'})

    def add_command(self, **kw):
        self.choices.append(kw | {'type': 'command'})

    def add_separator(self):
        self.choices.append({'type': 'separator'})

    def keys(self):
        return ['activebackground', 'activeborderwidth', 'activeforeground',
            'background', 'bd', 'bg', 'borderwidth', 'cursor',
            'disabledforeground', 'fg', 'font', 'foreground', 'postcommand',
            'relief', 'selectcolor', 'takefocus', 'tearoff', 'tearoffcommand',
            'title', 'type']

    def _select(self, cell):
        """Called when a cell is selected by click or keyboard navigation."""
        self.selected = cell
        cell.style.backgroundColor = 'lightblue'

    def _unselect(self):
        if self.selected:
            self.selected.style.backgroundColor = self.kw['background']
            self.selected.style.color = self.kw['fg']
            self.selected = None
            if self.open_submenu:
                self.open_submenu.element.remove()
            self.open_submenu = None

    def _show_cascade(self, cell):
        global _selected
        submenu = cell.kw['menu']
        submenu._build()
        submenu.opener = cell
        cell.menu = self
        self.element <= submenu.element
        self.open_on_mouseenter = True
        master = self.master.element
        if self.toplevel:
            _selected = [self.master]
            submenu.element.style.left = f"{cell.abs_left - master.abs_left}px"
            submenu.element.style.top = f"{cell.abs_top - master.abs_top + cell.offsetHeight}px"
        else:
            submenu.element.style.left = f"{self.element.offsetWidth}px"
            submenu.element.style.top = f"{cell.abs_top - self.element.abs_top}px"
        submenu.element.style.display = 'block'
        self.open_submenu = submenu

    def _cell_enter(self, cell):
        self._unselect()
        if self.toplevel:
            # mouse enters a toplevel menu item
            cell.style.backgroundColor = 'lightblue'
            self._select(cell)
            if self.open_on_mouseenter:
                self._show_cascade(cell)
        else:
            if cell.firstChild.colSpan == 2:
                # ignore separator
                return
            opener = self.opener
            cell.style.backgroundColor = self.kw['activebackground']
            cell.style.color = '#fff'
            opener.style.backgroundColor = 'lightblue'
            self._select(cell)

    def _cell_leave(self, cell):
        if self.toplevel:
            cell.style.backgroundColor = self.kw['background']
        else:
            cell.style.backgroundColor = self.kw['background']
            cell.style.color = self.kw['fg']

    def _build(self):
        self._unselect()
        self.element = html.DIV()
        if self.toplevel:
            self.element = html.DIV(style=self._main_menu_style)
        else:
            self.element = html.DIV(style=self._submenu_style)
            self.table = html.TABLE(cellspacing=0)
            self.element <= self.table

        self.config(**self.kw)

        for choice in self.choices:
            if choice['type'] == 'separator':
                if not self.toplevel:
                    cell = html.TR(html.TD(html.HR(), colspan=2))
                    self.table <= cell
                continue
            else:
                label = choice.get('label', '').replace(' ', chr(160))

            if self.toplevel:
                cell = html.SPAN(label, style=self._main_menu_span_style)
                self.element <= cell
            else:
                arrow = html.SPAN()
                if choice['type'] == 'cascade':
                    arrow.html = '&#x25B6;'
                elif choice['type'] == 'separator':
                    arrow.html = '<hr>'
                else:
                    arrow.html = '&nbsp;'
                cell = html.TR(
                    html.TD(label, style=self._submenu_label_style) +
                    html.TD(arrow, style=self._submenu_arrow_style))
                self.table <= cell
            cell.menu = self
            cell.bind('mouseenter', lambda ev: self._cell_enter(ev.target))
            cell.bind('mouseleave', lambda ev: self._cell_leave(ev.target))
            if choice['type'] == 'cascade':
                cell.kw = choice
                cell.bind('click',
                    lambda ev, cell=cell: self._show_cascade(cell))


class Radiobutton(Widget):

    def __init__(self, master, text='', value=None, variable=None,
            **kw):
        self.master = master
        self.kw = kw
        self.radio = html.INPUT(type='radio', value=value, name='x')
        if variable:
            self.radio.bind('click', lambda ev: variable.set(ev.target.value))
        self.element = html.DIV(self.radio + html.SPAN(text))
        self.config(**kw)

    def keys(self):
        return ['activebackground', 'activeforeground', 'anchor',
            'background', 'bd', 'bg', 'bitmap', 'borderwidth', 'command',
            'compound', 'cursor', 'disabledforeground', 'fg', 'font',
            'foreground', 'height', 'highlightbackground', 'highlightcolor',
            'highlightthickness', 'image', 'indicatoron', 'justify',
            'offrelief', 'overrelief', 'padx', 'pady', 'relief',
            'selectcolor', 'selectimage', 'state', 'takefocus', 'text',
            'textvariable', 'tristateimage', 'tristatevalue', 'underline',
            'value', 'variable', 'width', 'wraplength']

class Text(Widget):

    def __init__(self, master, **kw):
        self.master = master
        self.kw = kw
        self.element = html.DIV(contenteditable=True,
            style={'text-align': 'left', 'background-color': '#fff',
                   'width' :'100%'})
        self.config(**kw)

    def index(self, position):
        el = self.element
        if position is END or position == "end":
            # END (or "end") corresponds to the position just after the last
            # character in the buffer.
            lines = self._get_text().split('\n')
            return len(lines) + 1, 0
        elif position is INSERT or position == "insert":
            # INSERT (or "insert") corresponds to the insertion cursor.
            sel = window.getSelection()
            if sel.anchorNode is javascript.NULL \
                    or sel.anchorNode is self.element \
                    or not self.element.contains(sel.anchorNode):
                lines = self._get_text().split('\n')
                return len(lines), len(lines[-1])
            else:
                return self._node_offset_to_row_column(sel.anchorNode,
                    sel.anchorOffset)
        elif isinstance(position, float):
            row, column = [int(x) for x in str(position).split('.')]
        elif isinstance(position, str):
            if '.' not in position:
                raise ValueError(f'bad text index "{position}"')
            row, column = position.split('.')
            row = int(row)
            if row <= 0:
                return [0, 0]
            # handle modifiers such as "+ 3 chars"
            delta_column = 0
            delta_row = 0
            regexp = '\s*([+-])\s*(\d+)\s*(chars|char|cha|ch|c|lines|line|lin|li|l)'
            while True:
                if mo := re.search(regexp, column):
                    column = column[:mo.start()] + column[mo.end():]
                    delta = int(mo.groups()[0] + mo.groups()[1])
                    if mo.groups()[2].startswith('c'):
                        delta_column += delta
                    else:
                        delta_row += delta
                else:
                    break

            # handle modifiers linestart / lineend
            if mo := re.search('(linestart|lineend)', column):
                s = mo.groups()[0]
                if s == 'linestart':
                    column = 0
                else:
                    column = 'end'

            # handle modifiers wordstart / wordend
            word_border = None
            if mo := re.search('(wordstart|wordend)', column):
                word_border = mo.groups()[0]
                column = column[:mo.start()] + column[mo.end():]

            row += delta_row
            lines = self.element.text.split('\n')
            if row > len(lines):
                return self.index(END)
            if column == 'end':
                line = lines[row - 1]
                column = len(line)
            else:
                line = lines[row - 1]
                column = min(len(line), int(column) + delta_column)
                if word_border == "wordstart":
                    while column and line[column - 1].isalnum():
                        column -= 1
                elif word_border == "wordend":
                    while column < len(line) and line[column].isalnum():
                        column += 1
        return row, column

    def grid(self, **kwargs):
        super().grid(**kwargs)
        h = window.getComputedStyle(self.master.element)['height']
        self.element.style.height = h

    def delete(self, position, end=None):
        row, column = self.index(position)
        _range = document.createRange()
        sel = window.getSelection()
        el = self.element
        _range.setStart(el.childNodes[row - 1], column)

        if end is not None:
            end_row, end_column = self._convert_position(end)
            if end_row >= len(el.childNodes):
                end_row = len(el.childNodes)
                end_column = len(el.childNodes[end_row].innerText)
            _range.setEnd(el.childNodes[end_row - 1], end_column)
        else:
            _range.setEnd(el.childNodes[row - 1], column + 1)

        sel.removeAllRanges()
        sel.addRange(_range)
        _range.deleteContents()

    def insert(self, position, text, tags=()):
        if not self.element.childNodes:
            lines = text.split('\n')
            self.element <= lines[0] # text node
            for line in lines[1:]:
                self.element <= html.DIV(line)
        elif position is END:
            lastChild = self.element.lastChild
            lines = text.split('\n')
            if lastChild.nodeType == 3:
                lastChild.nodeValue += lines[0]
                self.element <= (html.DIV(line) for line in lines[1:])
            else:
                self.element <= (html.DIV(line) for line in lines)
        elif position is INSERT:
            sel = window.getSelection()
            if sel is javascript.NULL \
                    or sel.anchorNode is self.element \
                    or not self.element.contains(sel.anchorNode):
                self.insert(END, text)
            else:
                self.insert(*self.index(INSERT), text)
        else:
            row, column = self.index(position)
            element_text = self._get_text()
            lines = element_text.split('\n')
            if row > len(lines):
                return self.insert(END, text)
            line = lines[row - 1]

            node, offset = self._row_column_to_node_offset(row, column)
            if node.nodeType == 1 and node.nodeName == 'BR':
                node.parentNode.replaceChild(document.createTextNode(text), node)
            else:
                node.nodeValue = node.nodeValue[:offset] + text + \
                    node.nodeValue[offset:]

    def keys(self):
        return ['autoseparators', 'background', 'bd', 'bg', 'blockcursor',
            'borderwidth', 'cursor', 'endline', 'exportselection', 'fg', 'font',
            'foreground', 'height', 'highlightbackground', 'highlightcolor',
            'highlightthickness', 'inactiveselectbackground',
            'insertbackground', 'insertborderwidth', 'insertofftime',
            'insertontime', 'insertunfocussed', 'insertwidth', 'maxundo',
            'padx', 'pady', 'relief', 'selectbackground', 'selectborderwidth',
            'selectforeground', 'setgrid', 'spacing1', 'spacing2', 'spacing3',
            'startline', 'state', 'tabs', 'tabstyle', 'takefocus', 'undo',
            'width', 'wrap', 'xscrollcommand', 'yscrollcommand']

    def _get_text(self):
        text = ''
        previous = None
        for child in self.element.childNodes:
            if previous and child.nodeType == 1 \
                    and child.nodeName == 'DIV':
                text += '\n'
            if child.nodeType == 3:
                text += child.nodeValue.strip()
            elif child.nodeType == 1:
                child = child.firstChild
                if child.nodeType == 3:
                    text += child.nodeValue.strip()
            previous = child
        return text

    def _row_column_to_node_offset(self, row, column):
        line = 1
        col = 0
        previous = None

        for child in self.element.childNodes:
            if child.nodeType == 3:
                node_value = child.nodeValue
                node_text = node_value.strip()
                node_lines = node_value.split('\n')
                offset = 0
                for i, node_line in enumerate(node_lines):
                    if row == line + i:
                        return child, min(column + offset, len(node_line))
                    offset += len(node_line) + 1
                line += len(node_lines) - 1
            elif child.nodeType == 1:
                if previous and child.nodeName == 'DIV':
                    line += 1
                    col = 0
                for child in child.childNodes:
                    if child.nodeType == 3:
                        node_value = child.nodeValue
                        node_lines = node_value.split('\n')
                        offset = 0
                        for i, node_line in enumerate(node_lines):
                            col = 0
                            if not node_line and i == len(node_lines) - 1:
                                # ignore last empty line
                                continue
                            if row == line + i:
                                return child, min(column + offset, len(node_line))
                            offset += len(node_line) + 1
                            col = len(node_line)
                        line += len(node_lines) - 1
                    elif child.nodeType == 1:
                        if child.nodeName == 'BR' and column == 0:
                            node_line = ''
                            if row == line:
                                return child, 0
            previous = child

    def _node_offset_to_row_column(self, node, node_offset):
        line = 1
        col = 0
        previous = None

        for child in self.element.childNodes:
            if child.nodeType == 3:
                node_value = child.nodeValue
                node_text = node_value.strip()
                node_lines = node_value.split('\n')
                offset = 0
                for i, node_line in enumerate(node_lines):
                    if child is node and offset <= node_offset < offset + len(node_line):
                        return line + i, node_offset
                    offset += len(node_line) + 1
                if child is node:
                    return line + i, len(node_line)
                line += len(node_lines) - 1
            elif child.nodeType == 1:
                if previous and child.nodeName == 'DIV':
                    line += 1
                    col = 0
                for child in child.childNodes:
                    if child.nodeType == 3:
                        node_value = child.nodeValue
                        node_lines = node_value.split('\n')
                        offset = 0
                        for i, node_line in enumerate(node_lines):
                            col = 0
                            if not node_line and i == len(node_lines) - 1:
                                # ignore last empty line
                                continue
                            if child is node and offset <= node_offset < offset + len(node_line):
                                return line + i, node_offset
                            offset += len(node_line) + 1
                            col = len(node_line)
                        line += len(node_lines) - 1
                    elif child.nodeType == 1:
                        if child.nodeName == 'BR' and column == 0:
                            node_line = ''
                            if child is node:
                                return line, 0
            previous = child

class _KeyEventState:
    ignore = False

def _get_rank(elt):
    # return rank of element in its parentNode
    for rank, child in enumerate(elt.parentNode.childNodes):
        if child is elt:
            return rank

@document.bind('keydown')
def _keyboard_move_selection(event):
    """If an option is currently selected in the main menu, the selection
    can be changed by keyboard keys "ArrowRight" or "ArrowLeft".
    """
    if _KeyEventState.ignore:
        return
    if not _selected or not _selected[0].menu \
            or not _selected[0].menu.selected:
        print('pas de sélection')
        return
    menu = _selected[0].menu
    if event.key == 'ArrowRight':
        rank = _get_rank(menu.selected)
        if rank < len(menu.choices) - 1:
            menu._cell_enter(menu.selected.nextSibling)
            _KeyEventState.ignore = True
        return
    elif event.key == 'ArrowLeft':
        rank = _get_rank(menu.selected)
        if rank > 0:
            menu._cell_enter(menu.selected.previousSibling)
            _KeyEventState.ignore = True
        return

    # get the last selected option in an open menu
    menu = _selected[0].menu
    while True:
        if menu.selected:
            selected = menu.selected
        if menu.open_submenu:
            menu = menu.open_submenu
        else:
            break

    if event.key == 'ArrowDown':
        menu = selected.menu
        if menu.toplevel:
            if menu.open_submenu:
                # select first option in submenu
                cell = menu.open_submenu.table.firstChild
                menu.open_submenu._cell_enter(cell)
                _KeyEventState.ignore = True
        else:
            rank = _get_rank(menu.selected)
            while rank < len(menu.choices) - 1:
                candidate = selected.parentNode.childNodes[rank + 1]
                if candidate.firstChild.colSpan == 2: # separator
                    rank += 1
                else:
                    menu._cell_enter(candidate)
                    _KeyEventState.ignore = True
                    break

    elif event.key == 'ArrowUp':
        menu = selected.menu
        if not menu.toplevel:
            rank = _get_rank(menu.selected)
            while rank > 0:
                candidate = selected.parentNode.childNodes[rank - 1]
                if candidate.firstChild.colSpan == 2: # separator
                    rank -= 1
                else:
                    menu._cell_enter(candidate)
                    _KeyEventState.ignore = True
                    break

@document.bind('keyup')
def _keyup(event):
    _KeyEventState.ignore = False

def mainloop():
    for item in _loops:
        item.mainloop()
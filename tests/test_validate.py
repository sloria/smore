# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import pytest

from marshmallow import fields
from marshmallow.exceptions import UnmarshallingError
from webargs import Arg, ValidationError as WebargsValidationError

from smore.validate import ValidationError

class TestValidationError:

    def test_marshmallow_validation(self):
        def validator(val):
            raise ValidationError('oh no')

        f = fields.Field(validate=validator)
        with pytest.raises(UnmarshallingError):
            f.deserialize('')

    def test_webargs_validation(self):
        def validator(val):
            raise ValidationError('oh no')

        a = Arg(validate=validator)
        with pytest.raises(WebargsValidationError):
            a.validated('', '')

    def test_webargs_validation_with_status_code(self):

        def validator(val):
            raise ValidationError('denied', status_code=401)
        a = Arg(validate=validator)
        with pytest.raises(WebargsValidationError) as excinfo:
            a.validated('', '')
        exc = excinfo.value
        assert exc.status_code == 401


# WTForms

from smore.validate.wtforms import from_wtforms, make_converter
from wtforms.validators import AnyOf, NoneOf, Length

class TestWTFormsValidation:

    def test_from_wtforms(self):
        field = fields.Field(
            validate=from_wtforms([AnyOf(['red', 'blue'])])
        )

        assert field.deserialize('red') == 'red'
        with pytest.raises(UnmarshallingError) as excinfo:
            field.deserialize('green')
        assert 'Invalid value' in str(excinfo)

    def test_from_wtforms_multi(self):
        field = fields.Field(
            validate=from_wtforms(
                [
                    Length(min=4),
                    NoneOf(['nil', 'null', 'NULL'])
                ]
            )
        )
        assert field.deserialize('thisisfine') == 'thisisfine'
        with pytest.raises(UnmarshallingError) as excinfo:
            field.deserialize('bad')
        assert 'Field must be at least 4 characters long' in str(excinfo)
        with pytest.raises(UnmarshallingError) as excinfo:
            field.deserialize('null')
        assert "Invalid value, can't be any of: nil, null, NULL." in str(excinfo)

        with pytest.raises(UnmarshallingError) as excinfo:
            field.deserialize('nil')
        # both errors are returned
        assert "Invalid value, can't be any of: nil, null, NULL." in str(excinfo)
        assert 'Field must be at least 4 characters long' in str(excinfo)

    def test_from_wtforms_with_translation(self):
        field = fields.Field(
            validate=from_wtforms(
                [
                    Length(max=1)
                ],
                locales=['de_DE', 'de']
            )
        )
        with pytest.raises(UnmarshallingError) as excinfo:
            field.deserialize('toolong')
        # lol
        validation_msg = excinfo.value.underlying_exception.args[0]
        assert 'Feld kann nicht l\xe4nger als 1 Zeichen sein.' in validation_msg

    def test_make_converter(self):
        f = make_converter(['de_DE', 'de'])
        field = fields.Field(
            validate=f(
                [
                    Length(max=1)
                ],
                locales=['de_DE', 'de']
            )
        )
        with pytest.raises(UnmarshallingError) as excinfo:
            field.deserialize('toolong')
        validation_msg = excinfo.value.underlying_exception.args[0]
        assert 'Feld kann nicht l\xe4nger als 1 Zeichen sein.' in validation_msg

# Colander

from smore.validate.colander import from_colander
from colander import ContainsOnly

class TestColanderValidation:
    def test_from_colander(self):
        field = fields.Field(
            validate=from_colander([ContainsOnly([1])])
        )
        assert field.deserialize([1]) == [1]
        with pytest.raises(UnmarshallingError) as excinfo:
            field.deserialize([2])
        assert 'One or more of the choices you made was not acceptable' in str(excinfo)


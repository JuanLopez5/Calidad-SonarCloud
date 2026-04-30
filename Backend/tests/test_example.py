"""
Tests de ejemplo usando patrón AAA (Arrange-Act-Assert)
"""
import pytest
import sys


def test_example_pass():
    """Test de ejemplo que siempre pasa"""
    # Arrange
    num1 = 1
    num2 = 1
    expected = 2
    
    # Act
    result = num1 + num2
    
    # Assert
    assert result == expected


def test_example_string():
    """Test de ejemplo con strings"""
    # Arrange
    word1 = "Hello"
    word2 = "World"
    expected = "Hello World"
    
    # Act
    result = word1 + " " + word2
    
    # Assert
    assert result == expected


def test_list_operations():
    """Test de operaciones con listas"""
    # Arrange
    my_list = [1, 2, 3]
    new_item = 4
    
    # Act
    my_list.append(new_item)
    
    # Assert
    assert len(my_list) == 4
    assert new_item in my_list
